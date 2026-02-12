"""
IEEE-style paper outline generation.

Creates structured outlines with sections and bullet points.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class Section:
    """Represents a paper section."""
    
    title: str
    level: int  # 1=section, 2=subsection, 3=subsubsection
    bullet_points: List[str] = None
    subsections: List['Section'] = None
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.bullet_points is None:
            self.bullet_points = []
        if self.subsections is None:
            self.subsections = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'title': self.title,
            'level': self.level,
            'bullet_points': self.bullet_points,
            'subsections': [s.to_dict() for s in self.subsections]
        }


@dataclass
class PaperOutline:
    """Complete IEEE paper outline."""
    
    title: str
    abstract: Optional[str] = None
    sections: List[Section] = None
    
    def __post_init__(self):
        """Initialize defaults."""
        if self.sections is None:
            self.sections = []
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON."""
        data = {
            'title': self.title,
            'abstract': self.abstract,
            'sections': [s.to_dict() for s in self.sections]
        }
        return json.dumps(data, indent=indent)
    
    def to_markdown(self) -> str:
        """Convert to Markdown outline."""
        lines = [f"# {self.title}\n"]
        
        if self.abstract:
            lines.append("## Abstract\n")
            lines.append(self.abstract)
            lines.append("")
        
        for section in self.sections:
            lines.extend(self._format_section(section))
        
        return '\n'.join(lines)
    
    def _format_section(self, section: Section, base_level: int = 1) -> List[str]:
        """Format section recursively."""
        lines = []
        
        # Section heading
        heading_level = section.level + base_level
        heading = '#' * heading_level
        lines.append(f"\n{heading} {section.title}\n")
        
        # Bullet points
        for bullet in section.bullet_points:
            indent = '  ' * (section.level - 1)
            lines.append(f"{indent}- {bullet}")
        
        if section.bullet_points:
            lines.append("")
        
        # Subsections
        for subsection in section.subsections:
            lines.extend(self._format_section(subsection, base_level))
        
        return lines


class OutlineGenerator:
    """Generate IEEE-style paper outlines using LLM."""
    
    # Default IEEE paper structure
    DEFAULT_SECTIONS = [
        "Introduction",
        "Related Work",
        "Proposed Approach",
        "Experimental Setup",
        "Results and Evaluation",
        "Discussion",
        "Conclusion",
    ]
    
    def __init__(self, llm, audit_logger=None):
        """
        Initialize outline generator.
        
        Args:
            llm: LLM instance for generating outline content
            audit_logger: Optional audit logger
        """
        self.llm = llm
        self.audit_logger = audit_logger
    
    def generate_outline(self, topic: str, num_sections: int = 7,
                        include_related_work: bool = True,
                        deterministic: bool = False) -> PaperOutline:
        """
        Generate IEEE-style outline for a paper topic.
        
        Args:
            topic: Paper topic/title
            num_sections: Number of main sections (default: 7)
            include_related_work: Include "Related Work" section
            deterministic: Use temperature=0 for reproducibility
            
        Returns:
            PaperOutline with sections and bullet points
        """
        # Build prompt for outline generation
        prompt = self._build_outline_prompt(topic, num_sections, include_related_work)
        
        # Generate outline using LLM
        temp = 0.0 if deterministic else 0.5
        result = self.llm.generate(prompt, temperature=temp, max_tokens=1024)
        
        # Parse outline from LLM response
        outline = self._parse_outline_response(topic, result['text'])
        
        if self.audit_logger:
            self.audit_logger.log_event({
                'event': 'outline_generation',
                'topic': topic,
                'num_sections': len(outline.sections),
                'deterministic': deterministic
            })
        
        return outline
    
    def _build_outline_prompt(self, topic: str, num_sections: int,
                             include_related_work: bool) -> str:
        """Build prompt for outline generation."""
        sections_list = self.DEFAULT_SECTIONS if include_related_work else [
            s for s in self.DEFAULT_SECTIONS if s != "Related Work"
        ]
        
        sections_list = sections_list[:num_sections]
        sections_str = '\n'.join(f"- {s}" for s in sections_list)
        
        return f"""Generate an IEEE-style paper outline for the following topic:

TOPIC: {topic}

Create a structured outline with the following sections:
{sections_str}

For each section, provide:
1. Section title
2. 3-5 key bullet points

Format the outline as follows:

## Section Name
- Key point 1
- Key point 2
- Key point 3
- Key point 4

Do NOT include Introduction/Conclusion bullet points, only section headers.
Focus on technical content and research methodology.

OUTLINE:
"""
    
    def _parse_outline_response(self, topic: str, response: str) -> PaperOutline:
        """
        Parse LLM response into PaperOutline structure.
        
        Args:
            topic: Paper topic
            response: LLM-generated outline text
            
        Returns:
            PaperOutline object
        """
        import re
        
        outline = PaperOutline(title=topic)
        
        # Split by section headers (## Section Name)
        section_pattern = r'##\s+(.+?)(?=##|$)'
        matches = re.finditer(section_pattern, response, re.DOTALL)
        
        for match in matches:
            section_text = match.group(1).strip()
            
            # Extract section title (first line)
            lines = section_text.split('\n')
            if not lines:
                continue
            
            section_title = lines[0].strip()
            
            # Extract bullet points
            bullet_points = []
            for line in lines[1:]:
                line = line.strip()
                if line.startswith('-'):
                    bullet_points.append(line[1:].strip())
            
            section = Section(
                title=section_title,
                level=1,
                bullet_points=bullet_points
            )
            outline.sections.append(section)
        
        return outline