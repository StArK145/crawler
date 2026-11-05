from typing import List, Dict, Any, Optional
from src.stage3_ast.m25_ast_schema import PureExpr, ElementNode, TextNode, LoopNode, ComponentCall, ComponentDefinition

class AngularEmitter:
    """
    Angular 19+ Standalone Component Emitter.
    Focuses on preserving layout integrity using host: { 'class': 'contents' }.
    """

    def emit_angular_expression(self, expr: PureExpr) -> str:
        """
        Translates PureExpr into Angular template expressions.
        """
        if expr.value is not None:
            if isinstance(expr.value, str):
                return f"'{expr.value}'"
            return str(expr.value)

        if expr.path:
            # Angular usually references component properties directly.
            # We remove 'props.' to match the component class property names.
            path = expr.path
            if path.startswith("props."):
                path = path[6:]
            return path

        if expr.eq_left and expr.eq_right:
            left = self.emit_angular_expression(expr.eq_left)
            right = self.emit_angular_expression(expr.eq_right)
            return f"({left} === {right})"

        return "null"

    def emit_template(self, node: Any, ir_tailwind_map: Dict[str, str], cva_map: Dict[str, Any]) -> str:
        """
        Recursively emits Angular template HTML using new control flow.
        """
        if isinstance(node, ElementNode):
            tag = node.tag

            # 1. Handle class binding
            classes = ir_tailwind_map.get(node.ir_node_id, "")

            cva_variant_name = None
            for var_name, config in cva_map.items():
                if node.ir_node_id in config.get('affected_node_ids', []):
                    cva_variant_name = var_name
                    break

            class_attr = ""
            if cva_variant_name:
                func_name = cva_variant_name[0].lower() + cva_variant_name[1:]
                func_name = func_name.replace("Variant", "Variants")
                # Angular dynamic class binding [class]
                class_attr = f'[class]="{func_name}({{ variant: \'default\' }})"'
            elif classes:
                class_attr = f'class="{classes}"'

            # 2. Map other attributes to property bindings [attr]
            attrs = []
            for attr_name, expr in node.dom_attrs.items():
                val = self.emit_angular_expression(expr)
                attrs.append(f'[{attr_name}]="{val}"')

            if class_attr:
                attrs.append(class_attr)

            attr_str = " " + " ".join(attrs) if attrs else ""

            # 3. Recursively emit children
            children_html = "".join([self.emit_template(child, ir_tailwind_map, cva_map) for child in node.children])

            return f"<{tag}{attr_str}>{children_html}</{tag}>"

        elif isinstance(node, TextNode):
            expr_val = self.emit_angular_expression(node.value)
            # Angular interpolation syntax {{ ... }}
            text = f"{{{{ {expr_val} }}}}"
            if node.preserve_inline_space:
                return f'{" "}{text}'
            return text

        elif isinstance(node, LoopNode):
            iterable = self.emit_angular_expression(node.iterable)
            item_var = node.item_var
            index_var = node.index_var
            key_expr = self.emit_angular_expression(node.key_expr)

            body_html = "".join([self.emit_template(child, ir_tailwind_map, cva_map) for child in node.body])

            # Angular 17+ @for control flow
            return f"@for ({item_var} of {iterable}; track {key_expr}) {{ {body_html} }}"

        elif isinstance(node, ComponentCall):
            tag = node.component_name
            props_attrs = []
            for prop_name, expr in node.props.items():
                val = self.emit_angular_expression(expr)
                props_attrs.append(f'[{prop_name}]="{val}"')

            attr_str = " " + " ".join(props_attrs) if props_attrs else ""
            return f"<{tag}{attr_str}></{tag}>"

        return ""

    def emit_component(self, component_def: ComponentDefinition, ir_tailwind_map: Dict[str, str], cva_map: Dict[str, Any]) -> str:
        """
        Generates an Angular Standalone Component .ts file.
        """
        # Generate property declarations
        props_decls = []
        for prop_name, prop_type in component_def.props_schema.items():
            # Simple TS type mapping
            ts_type = prop_type if prop_type in ["string", "number", "boolean"] else "any"
            props_decls.append(f"  @Input() {prop_name}: {ts_type};")

        props_body = "\n".join(props_decls)

        # Generate template
        template_html = self.emit_template(component_def.root, ir_tailwind_map, cva_map)

        # Component name
        component_name = component_def.name

        # Assemble the @Component decorator and class
        # Crucial: host: { 'class': 'contents' } prevents the host element from breaking flex/grid layouts
        sfc = f"""import {{ Component, Input }} from '@angular/core';

@Component({{
  selector: '{component_name.lower()}',
  standalone: true,
  template: `{template_html}`,
  host: {{
    'class': 'contents'
  }}
}})
export class {component_name} {{
{props_body}
}}
"""
        return sfc
