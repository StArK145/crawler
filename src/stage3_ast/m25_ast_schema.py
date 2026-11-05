from typing import List, Dict, Union, Literal, Annotated, Optional
from pydantic import BaseModel, Field

class PureExpr(BaseModel):
    """
    A Turing-incomplete expression for the AST.
    Supports literals, property paths (e.g., 'props.title'), and equality checks.
    """
    # Literal value: string, number, or boolean
    value: Union[str, float, int, bool, None] = None
    # Property path for dynamic binding: e.g., 'props.title'
    path: Optional[str] = None
    # Simple equality check: expr == other_expr
    # We use a tuple of two PureExprs to represent the comparison
    # Note: Pydantic might need Recursive models for this, but for the schema
    # we define the components of the comparison.
    eq_left: Optional['PureExpr'] = None
    eq_right: Optional['PureExpr'] = None

    class Config:
        # Allow recursive models
        arbitrary_types_allowed = True

# Forward reference for ASTNode to allow recursive children/body
ASTNode = Annotated[
    Union[
        'ElementNode',
        'TextNode',
        'LoopNode',
        'ComponentCall'
    ],
    Field(discriminator='kind')
]

class ElementNode(BaseModel):
    kind: Literal["element"] = "element"
    ir_node_id: str
    tag: str
    dom_attrs: Dict[str, PureExpr]
    children: List[ASTNode]

class TextNode(BaseModel):
    kind: Literal["text"] = "text"
    value: PureExpr
    preserve_inline_space: bool

class LoopNode(BaseModel):
    kind: Literal["loop"] = "loop"
    iterable: PureExpr
    item_var: str
    index_var: str
    key_expr: PureExpr
    body: List[ASTNode]

class ComponentCall(BaseModel):
    kind: Literal["component"] = "component"
    component_name: str
    props: Dict[str, PureExpr]

# Update the Union with the actual classes
# In Pydantic v2, we use model_rebuild() for recursive models
ElementNode.model_rebuild()
TextNode.model_rebuild()
LoopNode.model_rebuild()
ComponentCall.model_rebuild()

# Re-defining ASTNode as a type alias for the Union
ASTNode = Union[ElementNode, TextNode, LoopNode, ComponentCall]

class ComponentDefinition(BaseModel):
    """
    The root definition of a canonical component.
    """
    name: str
    props_schema: Dict[str, str] # prop_name: type (e.g., 'title': 'string')
    root: ASTNode
