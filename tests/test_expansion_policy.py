import tempfile
import unittest
from pathlib import Path

from tests.test_blueprint import blueprint_payload
from tutor_engine.graph import Concept, ConceptGraph, ExpansionPolicy, Relation
from tutor_engine.service import TutorService
from tutor_engine.storage import JsonRepository


class ExpansionPolicyTests(unittest.TestCase):
    def test_recommends_unexpanded_coarse_concept(self) -> None:
        graph = ConceptGraph("cloud", concepts=[
            Concept("distributed", "分布式系统基础", metadata={"expandable": True})
        ])
        decision = ExpansionPolicy().evaluate(graph, graph.get_concept("distributed"))
        self.assertIsNotNone(decision)
        self.assertEqual(decision.action, "expansion_recommended")
        self.assertEqual(decision.suggested_child_count, 8)

    def test_skips_teachable_leaf_and_expanded_concept(self) -> None:
        graph = ConceptGraph("cloud", concepts=[
            Concept("leaf", "幂等性", metadata={"expandable": True, "leaf_teachable": True}),
            Concept("done", "网络基础", metadata={"expandable": True, "expansion_status": "expanded"}),
        ])
        policy = ExpansionPolicy()
        self.assertIsNone(policy.evaluate(graph, graph.get_concept("leaf")))
        self.assertIsNone(policy.evaluate(graph, graph.get_concept("done")))

    def test_recognizes_legacy_expansion_from_part_of_children(self) -> None:
        graph = ConceptGraph(
            "cloud",
            concepts=[
                Concept("container_images", "容器镜像", metadata={"expandable": True}),
                Concept("image_layers", "镜像分层"),
            ],
            relations=[Relation(
                "image_layers_part_of_container_images",
                "image_layers",
                "container_images",
                "part_of",
            )],
        )
        self.assertTrue(
            ExpansionPolicy.is_expanded(graph, graph.get_concept("container_images"))
        )
        self.assertIsNone(
            ExpansionPolicy().evaluate(graph, graph.get_concept("container_images"))
        )

    def test_next_requests_expansion_and_expand_unblocks_learning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = TutorService(JsonRepository(Path(directory)))
            service.create_subject("ml", "Machine Learning")
            service.create_blueprint("ml", blueprint_payload())
            recommendation = service.next_concept("ml")
            anchor = recommendation["concept"]
            self.assertEqual(recommendation["action"], "expansion_recommended")
            self.assertEqual(recommendation["expansion"]["anchor"], anchor)
            with self.assertRaisesRegex(ValueError, "expansion_recommended"):
                service.learn("ml", concept_id=anchor)

            result = service.expand_subject("ml", anchor, {
                "concepts": [{
                    "id": f"{anchor}_detail",
                    "name": "可教学细节",
                    "depth": 2,
                    "metadata": {
                        "scope_tags": ["supervised_learning"],
                        "goal_relevance": 0.5,
                        "leaf_teachable": True,
                    },
                }],
                "relations": [{
                    "id": f"{anchor}_detail_part_of_{anchor}",
                    "source": f"{anchor}_detail",
                    "target": anchor,
                    "type": "part_of",
                }],
            })
            self.assertEqual(result["expansion_status"], "expanded")
            self.assertIn("roadmap", result)
            roadmap_concepts = [
                concept
                for stage in result["roadmap"]["stages"]
                for concept in stage["concepts"]
            ]
            topic = next(item for item in roadmap_concepts if item["id"] == anchor)
            self.assertEqual(topic["node_type"], "topic")
            self.assertGreaterEqual(topic["child_progress"]["total_children"], 1)
            self.assertIn(
                f"{anchor}_detail",
                {item["id"] for item in topic["children"]},
            )
            metadata = service.repository.load_graph("ml").get_concept(anchor).metadata
            self.assertEqual(metadata["expansion_status"], "expanded")
            self.assertEqual(metadata["expansion_child_count"], 1)
            with self.assertRaisesRegex(ValueError, "aggregate topic"):
                service.learn("ml", concept_id=anchor)
            self.assertEqual(
                service.learn("ml", concept_id=f"{anchor}_detail")["status"],
                "learning",
            )


if __name__ == "__main__":
    unittest.main()
