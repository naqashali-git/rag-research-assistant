"""CLI commands for paper drafting."""

import click
import sys
from pathlib import Path
from rag_assistant.config import load_config, ConfigError
from rag_assistant.loader import load_documents
from rag_assistant.rag.engine import RAGEngine
from rag_assistant.security import init_security
from rag_assistant.audit.logger import get_audit_logger
from rag_assistant.paper import PaperDraftEngine
from rag_assistant.paper.formatter_latex import LaTeXFormatter
from rag_assistant.paper.formatter_docx import DocXFormatter
from rag_assistant.zotero import parse_zotero_export, CitationIndex


@click.group()
def forge():
    """Paper drafting and research commands."""
    pass


@forge.command()
@click.option('--topic', required=True, help='Paper topic/title')
@click.option('--format', type=click.Choice(['latex', 'word']), default='latex',
              help='Output format')
@click.option('--config', type=click.Path(exists=True), help='Config file path')
@click.option('--output', type=click.Path(), help='Output directory')
@click.option('--with-related-work', is_flag=True, default=True,
              help='Include Related Work section')
@click.option('--max-sources', type=int, default=20,
              help='Maximum sources per section')
@click.option('--deterministic', is_flag=True, default=True,
              help='Use temperature=0 for reproducible output')
@click.option('--template', type=click.Path(exists=True),
              help='Word template file (.docx)')
def draft(topic, format, config, output, with_related_work, max_sources,
         deterministic, template):
    """
    Draft a research paper using RAG.
    
    Generates:
    - IEEE-style outline
    - Full paper with citations
    - Output in LaTeX (main.tex + references.bib) or Word (.docx)
    
    Example:
        rag-assistant forge draft --topic "Machine Learning Applications" \\
          --format latex --with-related-work --max-sources 20 --deterministic
    """
    try:
        # Load configuration
        cfg = load_config(config)
        
        if not output:
            output = f"./output/{topic.replace(' ', '_')}"
        
        click.echo(click.style(f"\n[Drafting Paper: {topic}]", fg="blue", bold=True))
        click.echo(click.style(f"Format: {format.upper()}", fg="cyan"))
        click.echo(click.style(f"Output: {output}", fg="cyan"))
        click.echo()
        
        # Initialize security
        security_cfg = cfg.get_security_config()
        init_security(
            mode=security_cfg.get('mode', 'offline'),
            allowlist_domains=cfg.get_allowlist_domains(),
            audit_logger=get_audit_logger(cfg.get_audit_config())
        )
        
        # Initialize RAG engine
        click.echo(click.style("[Loading documents...]", fg="blue"))
        rag_engine = RAGEngine(cfg.data)
        documents = load_documents(cfg.data)
        
        if not documents:
            click.echo(click.style("⚠ No documents found.", fg="yellow"))
            return
        
        click.echo(click.style(f"✓ Loaded {len(documents)} document chunks", fg="green"))
        rag_engine.index_documents(documents)
        
        # Load Zotero for citations (optional)
        citation_index = None
        try:
            for doc_dir in cfg.get_document_dirs():
                doc_path = Path(doc_dir)
                for ext in ['.json', '.bib']:
                    zotero_file = doc_path / f"zotero{ext}"
                    if zotero_file.exists():
                        click.echo(click.style(f"[Loading Zotero: {zotero_file}]", fg="blue"))
                        items = parse_zotero_export(str(zotero_file))
                        citation_index = CitationIndex()
                        citation_index.add_items(items)
                        click.echo(click.style(f"✓ Loaded {citation_index.size()} citations", fg="green"))
                        break
        except Exception as e:
            click.echo(click.style(f"⚠ Warning: Could not load Zotero: {e}", fg="yellow"))
        
        # Initialize paper draft engine
        paper_engine = PaperDraftEngine(
            rag_engine=rag_engine,
            llm=rag_engine.llm,
            audit_logger=get_audit_logger(cfg.get_audit_config()),
            citation_index=citation_index
        )
        
        # Generate outline
        click.echo(click.style("\n[Generating outline...]", fg="blue"))
        draft_result = paper_engine.draft_paper(
            topic=topic,
            max_sources=max_sources,
            include_related_work=with_related_work,
            deterministic=deterministic
        )
        
        outline = draft_result['outline']
        sections = draft_result['sections']
        citations = draft_result['all_citations']
        
        click.echo(click.style(f"✓ Generated outline with {len(outline.sections)} sections", fg="green"))
        
        # Display outline preview
        click.echo(click.style("\n[Outline Preview]", fg="cyan"))
        for section in outline.sections:
            click.echo(f"  - {section.title}")
            for bullet in section.bullet_points[:2]:
                click.echo(f"    • {bullet[:60]}...")
        click.echo()
        
        # Draft sections
        click.echo(click.style("[Drafting sections...]", fg="blue"))
        for i, section in enumerate(sections, 1):
            click.echo(f"  {i}/{len(sections)} {section.title}... ({section.word_count} words)")
        
        click.echo(click.style(f"✓ Drafted {len(sections)} sections with {len(citations)} total citations", fg="green"))
        
        # Generate output
        click.echo(click.style(f"\n[Generating {format.upper()} output...]", fg="blue"))
        
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if format == 'latex':
            # Generate LaTeX
            main_tex, references_bib = LaTeXFormatter.format_paper(
                outline, sections, citations
            )
            
            (output_path / 'main.tex').write_text(main_tex)
            (output_path / 'references.bib').write_text(references_bib)
            
            click.echo(click.style(f"✓ Generated {output_path}/main.tex", fg="green"))
            click.echo(click.style(f"✓ Generated {output_path}/references.bib", fg="green"))
            click.echo()
            click.echo(click.style("Next steps:", fg="cyan"))
            click.echo("  1. Edit main.tex with your content")
            click.echo("  2. Compile: pdflatex main.tex")
            click.echo("  3. Generate bibliography: bibtex main")
        
        elif format == 'word':
            # Generate Word document
            if template:
                click.echo(click.style(f"[Using template: {template}]", fg="blue"))
                doc = DocXFormatter.format_paper_with_template(
                    outline, sections, citations, template
                )
            else:
                doc = DocXFormatter.format_paper_clean(
                    outline, sections, citations
                )
            
            doc_path = output_path / f"{topic.replace(' ', '_')}.docx"
            DocXFormatter.save_to_file(doc, str(doc_path))
            
            click.echo(click.style(f"✓ Generated {doc_path}", fg="green"))
        
        # Summary
        click.echo()
        click.echo(click.style("="*70, fg="cyan"))
        click.echo(click.style("Paper Draft Summary", fg="cyan", bold=True))
        click.echo(click.style("="*70, fg="cyan"))
        click.echo(f"Topic:       {topic}")
        click.echo(f"Sections:    {len(sections)}")
        click.echo(f"Citations:   {len(citations)}")
        click.echo(f"Total Words: {sum(s.word_count for s in sections)}")
        click.echo(f"Time:        {draft_result['metadata']['generation_time_ms']:.0f}ms")
        click.echo(f"Deterministic: {deterministic}")
        click.echo(click.style("="*70 + "\n", fg="cyan"))
    
    except ConfigError as e:
        click.echo(click.style(f"✗ Config error: {e}", fg="red"), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    forge()