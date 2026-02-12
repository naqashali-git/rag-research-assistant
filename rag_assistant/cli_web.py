"""CLI commands for web retrieval."""

import click
import sys
from pathlib import Path
from rag_assistant.config import load_config, ConfigError
from rag_assistant.retrievers.web_retriever import WebRetriever, QuerySanitizer
from rag_assistant.security import init_security
from rag_assistant.audit.logger import get_audit_logger


@click.group()
def web():
    """Web retrieval commands."""
    pass


@web.command('search')
@click.argument('query')
@click.option('--config', type=click.Path(exists=True), help='Config file path')
@click.option('--limit', type=int, default=5, help='Number of results')
@click.option('--format', type=click.Choice(['text', 'json']), default='text')
def web_search(query, config, limit, format):
    """
    Search web with sanitized query.
    
    Requires:
    - security.mode: egress in config.yaml
    - security.egress.enabled: true
    
    Example:
        rag-assistant web search "machine learning algorithms" --limit 10
    """
    try:
        cfg = load_config(config)
        
        # Check security mode
        security_cfg = cfg.get_security_config()
        if security_cfg.get('mode') != 'egress':
            click.echo(click.style(
                "✗ Web retrieval requires security.mode=egress in config.yaml",
                fg="red"
            ), err=True)
            sys.exit(1)
        
        if not security_cfg.get('egress', {}).get('enabled'):
            click.echo(click.style(
                "✗ Web retrieval disabled in config (security.egress.enabled=false)",
                fg="red"
            ), err=True)
            sys.exit(1)
        
        # Initialize security
        init_security(
            mode='egress',
            allowlist_domains=cfg.get_allowlist_domains(),
            sanitize_queries=True,
            audit_logger=get_audit_logger(cfg.get_audit_config())
        )
        
        # Sanitize query
        click.echo(click.style("[Sanitizing query...]", fg="blue"))
        try:
            sanitized_query = QuerySanitizer.sanitize(query)
        except Exception as e:
            click.echo(click.style(f"✗ Query rejected: {e}", fg="red"), err=True)
            sys.exit(1)
        
        click.echo(click.style(f"✓ Sanitized to: '{sanitized_query}'", fg="green"))
        
        # Create retriever
        allowlist = cfg.get_allowlist_domains()
        if not allowlist:
            click.echo(click.style(
                "✗ No allowlisted domains in config",
                fg="red"
            ), err=True)
            sys.exit(1)
        
        cache_dir = "./cache/web"
        retriever = WebRetriever(
            allowlist_domains=allowlist,
            cache_dir=cache_dir,
            audit_logger=get_audit_logger(cfg.get_audit_config())
        )
        
        click.echo(click.style(f"[Searching {', '.join(allowlist)}...]", fg="blue"))
        
        # Retrieve
        results = retriever.retrieve(sanitized_query, k=limit)
        
        if not results:
            click.echo(click.style("No results found.", fg="yellow"))
            return
        
        click.echo(click.style(f"✓ Found {len(results)} result(s)\n", fg="green"))
        
        if format == 'json':
            import json
            click.echo(json.dumps(results, indent=2))
        else:
            for i, result in enumerate(results, 1):
                click.echo(click.style(f"{i}. {result['source_path']}", fg="cyan"))
                click.echo(f"   Domain: {result.get('domain', 'unknown')}")
                click.echo(f"   Type: {result.get('doc_type', 'unknown')}")
                click.echo(f"   Preview: {result['content'][:200]}...")
                click.echo()
    
    except ConfigError as e:
        click.echo(click.style(f"✗ Config error: {e}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        sys.exit(1)


@web.command('clear-cache')
@click.option('--confirm', is_flag=True, help='Skip confirmation')
def clear_cache(confirm):
    """Clear web page cache."""
    cache_dir = Path('./cache/web')
    
    if not cache_dir.exists():
        click.echo(click.style("Cache directory not found.", fg="yellow"))
        return
    
    if not confirm:
        click.echo(f"This will delete all cached web pages in {cache_dir}")
        if not click.confirm("Continue?"):
            return
    
    import shutil
    shutil.rmtree(cache_dir)
    click.echo(click.style("✓ Cache cleared", fg="green"))


if __name__ == '__main__':
    web()