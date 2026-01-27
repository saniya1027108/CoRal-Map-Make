# src/utils/context_formatter.py
"""
Format structured context dictionary into readable text for LLM system prompts.
Converts JSON structure from context generation into clear, organized text.
"""
from typing import Dict, Any, List


def format_context_for_prompt(context_dict: Dict[str, Any]) -> str:
    """
    Convert structured context dictionary to formatted text for system prompt.
    
    Args:
        context_dict: Structured context with sections:
            - trial_identity
            - arm_mapping
            - terminology_bridge
            - data_organization
            - aggregation_rules
            - special_warnings
    
    Returns:
        Formatted multi-section text ready for LLM system prompt
    """
    sections = []
    
    # Header
    sections.append("=" * 80)
    sections.append("EXTRACTION GUIDE FOR THIS CLINICAL TRIAL")
    sections.append("=" * 80)
    sections.append("")
    
    # 1. Trial Identity
    if "trial_identity" in context_dict:
        sections.append("[1] TRIAL IDENTITY")
        sections.append("-" * 40)
        identity = context_dict["trial_identity"]
        for key, value in identity.items():
            if value:
                sections.append(f"{key}: {value}")
        sections.append("")
    
    # 2. Arm Mapping
    if "arm_mapping" in context_dict:
        sections.append("[2] ARM IDENTIFICATION (CRITICAL!)")
        sections.append("-" * 40)
        arm_mapping = context_dict["arm_mapping"]
        
        if "treatment_arm" in arm_mapping:
            sections.append("Treatment Arm:")
            treat = arm_mapping["treatment_arm"]
            for key, value in treat.items():
                if isinstance(value, list):
                    sections.append(f"  - {key}: {', '.join(str(v) for v in value)}")
                else:
                    sections.append(f"  - {key}: {value}")
            sections.append("")
        
        if "control_arm" in arm_mapping:
            sections.append("Control Arm:")
            control = arm_mapping["control_arm"]
            for key, value in control.items():
                if isinstance(value, list):
                    sections.append(f"  - {key}: {', '.join(str(v) for v in value)}")
                else:
                    sections.append(f"  - {key}: {value}")
            sections.append("")
    
    # 3. Terminology Bridge
    if "terminology_bridge" in context_dict:
        sections.append("[3] TERMINOLOGY BRIDGE")
        sections.append("-" * 40)
        sections.append("Generic term → Paper-specific terms:")
        sections.append("")
        
        bridge = context_dict["terminology_bridge"]
        for generic_term, specific_terms in bridge.items():
            if isinstance(specific_terms, list):
                terms_str = ", ".join(f'"{t}"' for t in specific_terms)
                sections.append(f"• {generic_term} = {terms_str}")
            else:
                sections.append(f"• {generic_term} = {specific_terms}")
        sections.append("")
    
    # 4. Data Organization
    if "data_organization" in context_dict:
        sections.append("[4] DATA ORGANIZATION & TABLE STRUCTURE")
        sections.append("-" * 40)
        
        org = context_dict["data_organization"]
        
        if "stratification" in org:
            sections.append("Stratification:")
            sections.append(f"  {org['stratification']}")
            sections.append("")
        
        if "tables" in org:
            for table_info in org["tables"]:
                if isinstance(table_info, dict):
                    table_num = table_info.get("table_number", "Unknown")
                    sections.append(f"Table {table_num}:")
                    for key, value in table_info.items():
                        if key != "table_number":
                            if isinstance(value, list):
                                sections.append(f"  - {key}: {', '.join(str(v) for v in value)}")
                            else:
                                sections.append(f"  - {key}: {value}")
                    sections.append("")
        sections.append("")
    
    # 5. Aggregation Rules
    if "aggregation_rules" in context_dict:
        sections.append("[5] AGGREGATION RULES (CRITICAL FOR STRATIFIED DATA!)")
        sections.append("-" * 40)
        
        rules = context_dict["aggregation_rules"]
        if isinstance(rules, list):
            for i, rule in enumerate(rules, 1):
                sections.append(f"{i}. {rule}")
        elif isinstance(rules, dict):
            for category, rule in rules.items():
                sections.append(f"• {category}:")
                sections.append(f"  {rule}")
        else:
            sections.append(str(rules))
        sections.append("")
    
    # 6. Special Warnings
    if "special_warnings" in context_dict:
        sections.append("[6] SPECIAL WARNINGS & EDGE CASES")
        sections.append("-" * 40)
        
        warnings = context_dict["special_warnings"]
        if isinstance(warnings, list):
            for warning in warnings:
                sections.append(f"⚠️  {warning}")
        elif isinstance(warnings, dict):
            for category, warning in warnings.items():
                sections.append(f"⚠️  {category}: {warning}")
        else:
            sections.append(f"⚠️  {warnings}")
        sections.append("")
    
    # Footer
    sections.append("=" * 80)
    sections.append("END OF EXTRACTION GUIDE")
    sections.append("=" * 80)
    
    return "\n".join(sections)


def format_simple_text_context(context_text: str) -> str:
    """
    Format plain text context (for backwards compatibility or fallback).
    
    Args:
        context_text: Plain text context
    
    Returns:
        Formatted text with header/footer
    """
    sections = []
    sections.append("=" * 80)
    sections.append("TRIAL CONTEXT (First 2 Pages)")
    sections.append("=" * 80)
    sections.append("")
    sections.append(context_text)
    sections.append("")
    sections.append("=" * 80)
    
    return "\n".join(sections)
