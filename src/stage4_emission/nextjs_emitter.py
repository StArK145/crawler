from typing import List, Dict, Any, Optional
from src.stage3_ast.m25_ast_schema import PureExpr, ElementNode, TextNode, LoopNode, ComponentCall, ComponentDefinition
from src.stage4_emission.react_emitter import ReactEmitter

class NextJsEmitter(ReactEmitter):
    """
    Next.js App Router Emitter.
    Translates Canonical AST into Next.js optimized components.
    """

    def emit_node(self, node: Any, ir_tailwind_map: Dict[str, str], cva_map: Dict[str, Any]) -> str:
        """
        Overrides emit_node to replace standard HTML primitives with Next.js optimized components.
        """
        if isinstance(node, ElementNode):
            tag = node.tag

            # 1. Handle Next.js <Link> replacement for <a>
            if tag == "a":
                href_expr = node.dom_attrs.get("href")
                href_val = self.emit_expression(href_expr) if href_expr else "'#'"

                # Extract other attrs except href
                attrs = []
                for attr_name, expr in node.dom_attrs.items():
                    if attr_name == "href": continue
                    val = self.emit_expression(expr)
                    attrs.append(f'{attr_name}={{ {val} }}')

                # Use next/link
                attr_str = f' href={href_val}'
                if attrs:
                    attr_str += " " + " ".join(attrs)

                children_jsx = "".join([self.emit_node(child, ir_tailwind_map, cva_map) for child in node.children])
                return f"<Link{attr_str}>{children_jsx}</Link>"

            # 2. Handle Next.js <Image> replacement for <img>
            if tag == "img":
                src_expr = node.dom_attrs.get("src")
                alt_expr = node.dom_attrs.get("alt")

                src_val = self.emit_expression(src_expr) if src_expr else "''"
                alt_val = self.emit_expression(alt_expr) if alt_expr else "''"

                # Standard Next.js Image attrs
                attrs = [
                    f'src={{{src_val}}}',
                    f'alt={{{alt_val}}}',
                    'unoptimized={true}'
                ]

                # Add any other custom attrs
                for attr_name, expr in node.dom_attrs.items():
                    if attr_name in ["src", "alt"]: continue
                    val = self.emit_expression(expr)
                    attrs.append(f'{attr_name}={{ {val} }}')

                attr_str = " " + " ".join(attrs)
                return f"<Image{attr_str} />"

            # Fallback to standard ReactEmitter logic for other elements
            return super().emit_node(node, ir_tailwind_map, cva_map)

        return super().emit_node(node, ir_tailwind_map, cva_map)

def emit_route_shell(page_ast: ComponentDefinition, ir_tailwind_map: Dict[str, str], cva_map: Dict[str, Any]) -> Dict[str, str]:
    """
    Generates a Next.js App Router structure: app/page.tsx and app/layout.tsx.
    """
    emitter = NextJsEmitter()

    # Generate page.tsx
    page_jsx = emitter.emit_component(page_ast, ir_tailwind_map, cva_map)

    page_content = f""""use client";
import React from 'react';
import Link from 'next/link';
import Image from 'next/image';

{page_jsx}

export default function Page() {{
  return <{page_ast.name} />;
}}
"""

    # Generate layout.tsx
    layout_content = """import './globals.css';
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ['latin'] });

export const metadata = {
  title: 'Generated Page',
  description: 'Deterministic Layout Emission',
};

export default function RootLayout({{ children }}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {children}
      </body>
    </html>
  );
}
"""

    return {
        "app/page.tsx": page_content,
        "app/layout.tsx": layout_content
    }
