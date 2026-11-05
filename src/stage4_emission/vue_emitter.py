from typing import List, Dict, Any, Optional
from src.stage3_ast.m25_ast_schema import PureExpr, ElementNode, TextNode, LoopNode, ComponentCall, ComponentDefinition

class VueEmitter:
    """
    Structural compiler for Vue 3 Single-File Components using <script setup>.
    """

    def emit_vue_expression(self, expr: PureExpr) -> str:
        """
        Translates PureExpr into Vue template syntax.
        Vue templates automatically unwrap refs, so we emit the path directly.
        """
        if expr.value is not None:
            if isinstance(expr.value, str):
                return f"'{expr.value}'"
            return str(expr.value)

        if expr.path:
            # In Vue templates, we usually reference props directly if they are in scope,
            # or via the variable name defined in script setup.
            # We remove the 'props.' prefix for template cleaner access.
            path = expr.path
            if path.startswith("props."):
                path = path[6:]
            return path

        if expr.eq_left and expr.eq_right:
            left = self.emit_vue_expression(expr.eq_left)
            right = self.emit_vue_expression(expr.eq_right)
            return f"({left} === {right})"

        return "null"

    def emit_template(self, node: Any, ir_tailwind_map: Dict[str, str], cva_map: Dict[str, Any]) -> str:
        """
        Recursively emits Vue template JSX for an AST node.
        """
        if isinstance(node, ElementNode):
            tag = node.tag

            # 1. Determine class binding
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
                class_attr = f':class="{func_name}({{ variant: \'default\' }})"'
            elif classes:
                class_attr = f'class="{classes}"'

            # 2. Map other attributes (v-bind)
            attrs = []
            for attr_name, expr in node.dom_attrs.items():
                val = self.emit_vue_expression(expr)
                attrs.append(f':{attr_name}="{val}"')

            if class_attr:
                attrs.append(class_attr)

            attr_str = " " + " ".join(attrs) if attrs else ""

            # 3. Recursively emit children
            children_html = "".join([self.emit_template(child, ir_tailwind_map, cva_map) for child in node.children])

            if not children_html and not attrs:
                # Vue doesn't have a standard self-closing for all tags in templates,
                # but we'll use standard HTML for common ones.
                return f"<{tag}{attr_str}></{tag}>"

            return f"<{tag}{attr_str}>{children_html}</{tag}>"

        elif isinstance(node, TextNode):
            expr_val = self.emit_vue_expression(node.value)
            # In Vue, double curly braces {{ }} are used for interpolation
            text = f"{{{{ {expr_val} }}}}"
            if node.preserve_inline_space:
                return f'{" "}{text}'
            return text

        elif isinstance(node, LoopNode):
            iterable = self.emit_vue_expression(node.iterable)
            item_var = node.item_var
            index_var = node.index_var
            key_expr = self.emit_vue_expression(node.key_expr)

            body_html = "".join([self.emit_template(child, ir_tailwind_map, cva_map) for child in node.body])

            # Vue v-for syntax: v-for="(item, index) in iterable"
            return f'<template v-for="({item_var}, {index_var}) in {iterable}" :key="{key_expr}">{body_html}</template>'

        elif isinstance(node, ComponentCall):
            tag = node.component_name
            props_attrs = []
            for prop_name, expr in node.props.items():
                val = self.emit_vue_expression(expr)
                props_attrs.append(f':{prop_name}="{val}"')

            attr_str = " " + " ".join(props_attrs) if props_attrs else ""
            return f"<{tag}{attr_str} />"

        return ""

    def emit_sfc(self, component_def: ComponentDefinition, ir_tailwind_map: Dict[str, str], cva_map: Dict[str, Any]) -> str:
        """
        Generates a Vue 3 Single-File Component with <script setup>.
        """
        # 1. Generate defineProps
        props_list = []
        for prop_name, prop_type in component_def.props_schema.items():
            # Map types to TS (simplified)
            ts_type = prop_type if prop_type in ["string", "number", "boolean"] else "any"
            props_list.append(f"  {prop_name}: {ts_type};")

        props_body = "\n" + "\n".join(props_list) + "\n" if props_list else ""
        define_props = f"const props = defineProps<{props_body}>();"

        # 2. Define Options
        define_options = "defineOptions({ inheritAttrs: false });"

        # 3. Generate Template
        template_html = self.emit_template(component_def.root, ir_tailwind_map, cva_map)

        # Assemble SFC
        sfc = f"""<script setup lang="ts">
{define_props}
{define_options}
</script>

<template>
  {template_html}
</template>
"""
        return sfc
