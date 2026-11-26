import unittest

from turn_routing_preview import infer_operations_program, route_turn


def route(text: str):
    return route_turn(
        text,
        main_model="fictional-main",
        fast_model="fictional-fast",
        fast_routing=True,
        main_context_window=8192,
        fast_context_window=4096,
        configured_reasoning="auto",
    )


class RoutingTests(unittest.TestCase):
    def test_short_chat_uses_fast_local_model_without_tools(self) -> None:
        result = route("Good morning!")
        self.assertEqual(result.model, "fictional-fast")
        self.assertEqual(result.kind, "fast_chat")
        self.assertEqual(result.tool_names, ())

    def test_operations_request_stays_on_main_model(self) -> None:
        result = route("Is the demo Rust server healthy? Is its scheduled task running?")
        self.assertEqual(result.model, "fictional-main")
        self.assertEqual(result.kind, "operations")
        self.assertIn("operations_status", result.tool_names)
        self.assertIn("program_read_file", result.tool_names)
        self.assertIn("program_search_text", result.tool_names)
        self.assertNotIn("write_file", result.tool_names)

    def test_iw4x_and_zomboid_requests_route_to_operations_profiles(self) -> None:
        result = route("Is the demo IW4x server online?")
        self.assertEqual(result.kind, "operations")
        self.assertEqual(infer_operations_program("Inspect the demo IW4x server"), "modern_warfare")
        self.assertEqual(infer_operations_program("Inspect the demo Project Zomboid server"), "zomboid")

    def test_program_fix_routes_read_tools_and_workspace_proposal_tools(self) -> None:
        result = route("Draft a patch to fix the sample Rust server config and write it in the workspace.")
        self.assertEqual(result.kind, "operations")
        self.assertIn("program_read_file", result.tool_names)
        self.assertIn("program_search_text", result.tool_names)
        self.assertIn("write_file", result.tool_names)
        self.assertIn("replace_text", result.tool_names)
        self.assertEqual(infer_operations_program("Inspect the demo Ollama setup"), "env_ai")

    def test_management_request_routes_guarded_control_tools(self) -> None:
        result = route("Ensure the demo managed programs are running.")
        self.assertEqual(result.kind, "operations")
        self.assertIn("program_control_capabilities", result.tool_names)
        self.assertIn("program_control", result.tool_names)

    def test_workspace_edit_routes_only_workspace_tools(self) -> None:

        result = route("Create a Python file in the sample workspace and run it.")
        self.assertEqual(result.kind, "workspace")
        self.assertIn("write_file", result.tool_names)
        self.assertIn("run_python", result.tool_names)
        self.assertNotIn("operations_status", result.tool_names)
