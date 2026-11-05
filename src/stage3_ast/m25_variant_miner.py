from typing import List, Dict, Set, Tuple, Any, Optional
from collections import defaultdict

class VariantMiner:
    """
    Deduplicates repetitive Tailwind class strings across similar elements
    to generate clean CVA (Class Variance Authority) configurations.
    """

    def compute_jaccard_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        """
        Returns the intersection size divided by the union size of two sets of Tailwind classes.
        """
        if not set_a and not set_b:
            return 1.0

        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)

        return len(intersection) / len(union)

    def mine_variants(self, ui_ir_nodes: List[Dict[str, Any]], similarity_threshold: float = 0.75) -> Dict[str, Any]:
        """
        Groups nodes by semantic role and tag, then clusters them by Tailwind similarity
        to extract CVA base classes and variants.
        """
        # 1. Group by (semantic_role, tag)
        groups = defaultdict(list)
        for node in ui_ir_nodes:
            role = node.get('semantic_role', 'generic')
            tag = node.get('tag', 'div')
            groups[(role, tag)].append(node)

        variant_configs = {}
        variant_counter = 0

        for (role, tag), nodes in groups.items():
            if len(nodes) < 3:
                continue

            # Extract class sets for each node in the group
            class_sets = []
            for node in nodes:
                # Assuming 'resolved_tailwind' is a space-separated string of classes
                classes = set(node.get('resolved_tailwind', '').split())
                class_sets.append((node.get('ir_node_id'), classes))

            # 2. Clustering based on Jaccard similarity
            # We use a simple greedy clustering: find a seed and cluster all similar nodes
            unclustered = list(range(len(class_sets)))

            while unclustered:
                seed_idx = unclustered[0]
                seed_id, seed_classes = class_sets[seed_idx]
                cluster = [seed_idx]

                for other_idx in unclustered[1:]:
                    other_id, other_classes = class_sets[other_idx]
                    if self.compute_jaccard_similarity(seed_classes, other_classes) >= similarity_threshold:
                        cluster.append(other_idx)

                # 3. Extract Base and Variants if cluster size >= 3
                if len(cluster) >= 3:
                    # Base classes are the intersection of all nodes in the cluster
                    all_cluster_sets = [class_sets[i][1] for i in cluster]
                    base_classes = set.intersection(*all_cluster_sets)

                    # Variants are the union of the disjoint classes across the cluster
                    all_disjoint = set()
                    for s in all_cluster_sets:
                        all_disjoint.update(s - base_classes)

                    # Generate a variant name based on role
                    variant_name = f"{role.capitalize()}Variant" if role != 'generic' else f"GenericVariant_{variant_counter}"
                    variant_counter += 1

                    # Build CVA config
                    # We group disjoint classes into "variants" based on their appearance
                    # In a real CVA, we'd look for mutually exclusive sets, but for the miner,
                    # we treat the collective disjoint set as the variant pool.
                    variant_configs[variant_name] = {
                        "base_classes": " ".join(sorted(list(base_classes))),
                        "variants": list(sorted(list(all_disjoint))),
                        "affected_node_ids": [class_sets[i][0] for i in cluster]
                    }

                # Remove the cluster from the unclustered list
                for idx in cluster:
                    if idx in unclustered:
                        unclustered.remove(idx)

        return variant_configs
