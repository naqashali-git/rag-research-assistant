"""
Paper draft generation engine using RAG.

Generates sections by querying documents and citing sources.
"""

from typing import Dict, List, Tuple, Optional, Any
import time
from rag_assistant.rag.engine import RAGEngine
from rag_assistant.zotero import CitationIndex
from .outline import PaperOutline, OutlineGenerator, Section


@dataclass
class DraftedSection:
    """A section of a drafted paper with citations."""
    
    title: str
    level: int
    content: str
    citations: List[Dict[str, Any]]  # List of cited sources
    word_count: int
    generation_time_ms: float


class PaperDraftEngine:
    """
    Generate paper drafts using RAG and document retrieval.
    
    Features:
    - IEEE outline generation
    - RAG-based section writing with citations
    - Multi-source retrieval and synthesis
    - Deterministic output (temperature=0)
    """
    
    def __init__(self, rag_engine: RAGEngine, llm, audit_logger=None,
                 citation_index: Optional[CitationIndex] = None):
        """
        Initialize paper draft engine.
        
        Args:
            rag_engine: RAGEngine for document retrieval
            llm: LLM for content generation
            audit_logger: Optional audit logger
            citation_index: Optional CitationIndex for bibliography
        """
        self.rag_engine = rag_engine
        self.llm = llm
        self.audit_logger = audit_logger
        self.citation_index = citation_index
        self.outline_generator = OutlineGenerator(llm, audit_logger)
    
    def draft_paper(self, topic: str, max_sources: int = 20,
                   include_related_work: bool = True,
                   deterministic: bool = True) -> Dict[str, Any]:
        """
        Draft a complete paper with outline and sections.
        
        Args:
            topic: Paper topic/title
            max_sources: Maximum sources to retrieve per section
            include_related_work: Include Related Work section
            deterministic: Use temperature=0 for reproducibility
            
        Returns:
            Dict with:
            - outline: PaperOutline
            - sections: List of DraftedSection objects
            - all_citations: Deduplicated list of all citations
            - metadata: Generation metadata
        """
        start_time = time.time()
        
        # 1. Generate outline
        outline = self.outline_generator.generate_outline(
            topic,
            include_related_work=include_related_work,
            deterministic=deterministic
        )
        
        # 2. Draft each section
        drafted_sections = []
        all_citations = {}  # citation_id -> citation
        
        for section in outline.sections:
            drafted = self._draft_section(
                section,
                topic,
                max_sources=max_sources,
                deterministic=deterministic
            )
            drafted_sections.append(drafted)
            
            # Collect citations
            for citation in drafted.citations:
                all_citations[citation['citation_id']] = citation
        
        total_time = (time.time() - start_time) * 1000
        
        if self.audit_logger:
            self.audit_logger.log_event({
                'event': 'paper_draft',
                'topic': topic,
                'num_sections': len(drafted_sections),
                'total_citations': len(all_citations),
                'generation_time_ms': total_time,
                'deterministic': deterministic
            })
        
        return {
            'outline': outline,
            'sections': drafted_sections,
            'all_citations': list(all_citations.values()),
            'metadata': {
                'topic': topic,
                'generation_time_ms': total_time,
                'num_sections': len(drafted_sections),
                'num_citations': len(all_citations),
                'deterministic': deterministic
            }
        }
    
    def _draft_section(self, section: Section, topic: str,
                      max_sources: int, deterministic: bool) -> DraftedSection:
        """
        Draft a single section using RAG.
        
        Args:
            section: Section structure with bullets
            topic: Overall paper topic
            max_sources: Max sources to retrieve
            deterministic: Use temperature=0
            
        Returns:
            DraftedSection with content and citations
        """
        section_start = time.time()
        
        # Build section query from bullets
        query = self._build_section_query(topic, section)
        
        # Retrieve relevant documents
        query_embedding = self.rag_engine.embedder.embed_single(query)
        retrieved = self.rag_engine.vector_store.search(query_embedding, k=max_sources)
        
        # Build content prompt
        prompt = self._build_section_prompt(section, topic, query, retrieved)
        
        # Generate section content
        temp = 0.0 if deterministic else 0.7
        result = self.llm.generate(prompt, temperature=temp, max_tokens=800)
        
        section_time = (time.time() - section_start) * 1000
        
        return DraftedSection(
            title=section.title,
            level=section.level,
            content=result['text'],
            citations=[
                {
                    'citation_id': doc['citation_id'],
                    'source_path': doc['source_path'],
                    'page_or_section': doc['page_or_section'],
                    'doc_type': doc['doc_type']
                }
                for doc in retrieved
            ],
            word_count=len(result['text'].split()),
            generation_time_ms=section_time
        )
    
    def _build_section_query(self, topic: str, section: Section) -> str:
        """Build search query for section content."""
        bullets = ' '.join(section.bullet_points)
        return f"{topic}: {section.title} - {bullets}"
    
    def _build_section_prompt(self, section: Section, topic: str,
                             query: str, retrieved: List[Dict]) -> str:
        """Build prompt for section writing."""
        # Prepare context from retrieved documents
        context_parts = []
        for i, doc in enumerate(retrieved, 1):
            context_parts.append(
                f"[{i}] ({doc['source_path']} - {doc['page_or_section']}):\n{doc['content'][:300]}..."
            )
        context = "\n\n".join(context_parts)
        
        # Build bullet point list
        bullets_str = '\n'.join(f"- {b}" for b in section.bullet_points)
        
        return f"""Write a technical section for an IEEE conference paper.

PAPER TOPIC: {topic}
SECTION: {section.title}

KEY POINTS TO COVER:
{bullets_str}

CONTEXT FROM RELATED DOCUMENTS:
{context}

REQUIREMENTS:
- Write 200-400 words
- Use formal, technical language
- Cite sources using [n] notation corresponding to context references
- Each major claim should be supported by citations
- Include technical details and methodology where relevant
- Maintain IEEE paper conventions

SECTION CONTENT:
"""