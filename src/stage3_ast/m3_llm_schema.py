from typing import List, Dict, Union, Literal, Annotated
from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated as TypeAnnotated

# Regex constraints for naming
ComponentNameRegex = TypeAnnotated[str, StringConstraints(pattern=r"^[A-Z][A-Za-z0-9]{1,48}$")]
PropNameRegex = TypeAnnotated[str, StringConstraints(pattern=r"^[a-z][A-Za-z0-9]{1,48}$")]

class RenameComponent(BaseModel):
    kind: Literal["rename_component"] = "rename_component"
    old_name: str
    new_name: ComponentNameRegex

class RenameProp(BaseModel):
    kind: Literal["rename_prop"] = "rename_prop"
    component_name: str
    old_prop_name: str
    new_prop_name: PropNameRegex

class PropMapping(BaseModel):
    source_expr: str # Simplified for the schema; refers to the PureExpr path/value
    target_prop: PropNameRegex

class ExtractComponent(BaseModel):
    kind: Literal["extract_component"] = "extract_component"
    target_ir_node_id: str
    new_component_name: ComponentNameRegex
    prop_mappings: List[PropMapping]

# Discriminated Union for Refactoring Operations
RefactoringOperation = Annotated[
    Union[RenameComponent, RenameProp, ExtractComponent],
    Field(discriminator="kind")
]

class LLMRefactoringPlan(BaseModel):
    """
    A structured plan for refactoring a machine-generated AST into a human-readable
    canonical component library.
    """
    operations: List[RefactoringOperation]

def build_refactoring_prompt(baseline_ast_json: str, layout_summary_text: str) -> str:
    """
    Generates a high-precision prompt for the LLM to drive a structured refactoring pass.
    """
    return f"""You are an expert Frontend Architect. Your task is to refactor a machine-generated AST into a clean, semantic, and maintainable React component library.

### CONSTRAINTS:
1. Do NOT alter the DOM hierarchy.
2. Do NOT change ir_node_id mappings.
3. Do NOT invent new CSS classes or Tailwind strings.
4. Output ONLY a valid JSON object matching the LLMRefactoringPlan schema.

### INPUTS:
- Baseline AST (JSON):
{baseline_ast_json}

- Layout Summary:
{layout_summary_text}

### OBJECTIVE:
Analyze the AST and layout summary to perform:
- Semantic Renaming: Rename generic components (e.g., Component_123 -> UserProfileCard).
- Prop Refinement: Rename machine-generated props to descriptive names (e.g., prop_1 -> userName).
- Component Extraction: Identify repeated patterns and extract them into new components.

Refactor this machine-generated AST by outputting semantic renaming and extraction operations. Do NOT alter the DOM hierarchy or ir_node_id mappings.
"""
