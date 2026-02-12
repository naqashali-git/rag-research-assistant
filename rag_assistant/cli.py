"""
Main CLI for RAG Research Assistant.

Combines all subcommands: ask, ingest, cite, forge (draft), security, audit-log
"""

import click
from rag_assistant.cli_ask import ask_group
from rag_assistant.cli_ingest import ingest_group
from rag_assistant.cli_cite import cite_group
from rag_assistant.cli_paper import forge_group
from rag_assistant.cli_security import security_group
from rag_assistant.cli_audit import audit_group


@click.group()
@click.version_option()
def cli():
    """RAG Research Assistant - Local-first, security-constrained."""
    pass


# Add subgroups
cli.add_command(ask_group, 'ask')
cli.add_command(ingest_group, 'ingest')
cli.add_command(cite_group, 'cite')
cli.add_command(forge_group, 'forge')
cli.add_command(security_group, 'security')
cli.add_command(audit_group, 'audit-log')


if __name__ == '__main__':
    cli()