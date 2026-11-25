"""Exercise the numbered-layout CLI with real temporary files."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


CHECKER = Path(__file__).resolve().parents[1] / "plugins/adhcl/skills/adhcl-scaffold/scripts/ad_layout_check.py"


class LayoutCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "src").mkdir()

    def put(self, name, text=""):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def pair(self, number="1", dp="choice", fr="outcome", prefix="", test_prefix=""):
        token = f"dp{number}_{dp}"
        self.put(f"src/{prefix}{token}/pv{number}_impl.py", "pass\n")
        self.put(f"tests/{test_prefix}fr{number}_{fr}/scenario.py", token)
        return token

    def run_cli(self, *args):
        result = subprocess.run(
            [sys.executable, str(CHECKER), "--root", str(self.root), *args],
            text=True, capture_output=True, timeout=10,
        )
        return result.returncode, result.stdout + result.stderr

    def model(self, extra="", second=False):
        text = '''design "demo" { boundary = "This example" }
fr "outcome" {
  alias = "FR1"
  statement = "Produce an outcome"
}
dp "choice" {
  alias = "DP1"
  controls = [fr.outcome]
  decision = "selected"
  responsibility = "Control the outcome"
}
pv "impl" {
  alias = "PV1"
  realizes = [dp.choice]
  address = "src/dp1_choice/pv1_impl"
}
'''
        if second:
            text += '''fr "other" { alias = "FR2"
statement = "Produce another outcome" }
dp "other_choice" { alias = "DP2"
controls = [fr.other]
decision = "selected"
responsibility = "Control another outcome" }
pv "other_impl" { alias = "PV2"
realizes = [dp.other_choice] }
'''
        return self.put("spec/model.ad.hcl", text + extra)

    def test_empty_inventory_fails(self):
        code, out = self.run_cli("--expect", "uncoupled")
        self.assertEqual(code, 1, out)
        self.assertIn("empty", out.lower())
        self.assertIn("incomplete", out)

    def test_numbered_layout_succeeds_without_design_classification(self):
        self.pair()
        code, out = self.run_cli("--expect", "uncoupled", "--spec", str(self.model()))
        self.assertEqual(code, 0, out)
        self.assertIn("reference pattern: diagonal", out)
        self.assertIn("T", out)
        self.assertNotIn("structural classification", out)

    def test_missing_fr_pair_fails(self):
        self.put("src/dp1_choice/pv1_impl.py", "pass")
        code, out = self.run_cli()
        self.assertEqual(code, 1, out)
        self.assertIn("paired", out)
        self.assertIn("incomplete", out)

    def test_missing_dp_pair_fails(self):
        self.pair()
        self.put("tests/fr2_other/scenario.py", "nothing")
        code, out = self.run_cli()
        self.assertEqual(code, 1, out)
        self.assertIn("FR2", out)
        self.assertIn("incomplete", out)

    def test_missing_paired_test_token_fails(self):
        self.pair()
        self.put("tests/fr1_outcome/scenario.py", "pass")
        code, out = self.run_cli()
        self.assertEqual(code, 1, out)
        self.assertIn("paired-test token", out)
        self.assertIn("?", out)
        self.assertIn("incomplete", out)

    def test_missing_leaf_pv_fails(self):
        self.pair()
        (self.root / "src/dp1_choice/pv1_impl.py").unlink()
        code, out = self.run_cli()
        self.assertEqual(code, 1, out)
        self.assertIn("leaf DP", out)

    def test_source_direction_and_policy_are_separate(self):
        first = self.pair()
        self.pair("2", "other_choice", "other")
        self.put("src/dp2_other_choice/use.py", first)
        code, out = self.run_cli("--expect", "decoupled")
        self.assertEqual(code, 0, out)
        self.assertIn("reference pattern: acyclic", out)
        self.assertIn("DP order: DP1, DP2", out)
        self.assertIn("FR2 <- DP1", out)
        code, out = self.run_cli("--expect", "uncoupled")
        self.assertEqual(code, 1, out)

    def test_cycle_fails_only_explicit_decoupled_policy(self):
        first = self.pair()
        second = self.pair("2", "other_choice", "other")
        self.put("src/dp2_other_choice/use.py", first)
        self.put("src/dp1_choice/use.py", second)
        code, out = self.run_cli()
        self.assertEqual(code, 0, out)
        self.assertIn("reference pattern: cyclic", out)
        code, out = self.run_cli("--expect", "decoupled")
        self.assertEqual(code, 1, out)
        self.assertIn("cycle", out)

    def test_test_only_reference_does_not_enter_source_graph(self):
        first = self.pair()
        second = self.pair("2", "other_choice", "other")
        self.put("tests/fr1_outcome/scenario.py", f"{first} {second}")
        code, out = self.run_cli("--expect", "uncoupled")
        self.assertEqual(code, 0, out)
        self.assertIn("reference pattern: diagonal", out)
        self.assertIn("Test-text references", out)
        self.assertIn("FR1 <- DP2", out)
        self.assertIn("not executed", out)

    def test_zero_claim_with_source_token_is_review_warning(self):
        first = self.pair()
        self.pair("2", "other_choice", "other")
        # Keep the second PV label in step with the model.
        (self.root / "src/dp2_other_choice/pv2_impl.py").rename(self.root / "src/dp2_other_choice/pv2_other_impl.py")
        self.put("src/dp2_other_choice/use.py", first)
        spec = self.model('''influence {
from = [dp.choice]
to = fr.other
effect = "none"
because = "The outcome is isolated"
}
''', second=True)
        code, out = self.run_cli("--spec", str(spec))
        self.assertEqual(code, 0, out)
        self.assertIn("REVIEW WARNING", out)
        self.assertNotIn("contradict", out.lower())
        code, out = self.run_cli("--spec", str(spec), "--expect", "uncoupled")
        self.assertEqual(code, 1, out)

    def test_nested_layout_requires_direct_parent(self):
        self.pair()
        self.pair("1_1", "child", "child", "dp1_choice/wrapper/", "fr1_outcome/")
        code, out = self.run_cli()
        self.assertEqual(code, 1, out)
        self.assertIn("directly", out)

    def test_valid_nested_layout(self):
        self.pair()
        self.pair("1_1", "child", "child", "dp1_choice/", "fr1_outcome/")
        code, out = self.run_cli()
        self.assertEqual(code, 0, out)

    def test_parent_target_is_unresolved_at_leaf_scope(self):
        self.pair()
        self.pair("1_1", "child", "child", "dp1_choice/", "fr1_outcome/")
        self.pair("2", "other_choice", "other")
        self.put("src/dp2_other_choice/use.py", "dp1_choice")
        code, out = self.run_cli()
        self.assertEqual(code, 0, out)
        self.assertIn("unresolved parent scope", out)
        self.assertIn("DP1", out)

    def test_malformed_reserved_names_fail(self):
        self.pair()
        for name in ("dp2_Bad", "dp_thing", "pv1_Bad.py"):
            with self.subTest(name=name):
                path = self.put(f"src/dp1_choice/{name}", "")
                code, out = self.run_cli()
                self.assertEqual(code, 1, out)
                self.assertIn("malformed", out)
                path.unlink()

    def test_symlink_loop_is_reported_without_following(self):
        self.pair()
        (self.root / "src/dp1_choice/loop").symlink_to(self.root / "src", target_is_directory=True)
        code, out = self.run_cli()
        self.assertEqual(code, 1, out)
        self.assertIn("skipped symlink", out)

    def test_oversize_and_nontext_files_are_reported(self):
        self.pair()
        self.put("src/dp1_choice/large.txt", "x" * 2_000_001)
        (self.root / "src/dp1_choice/binary").write_bytes(b"\xff")
        code, out = self.run_cli()
        self.assertEqual(code, 1, out)
        self.assertIn("skipped oversize", out)
        self.assertIn("skipped unreadable", out)

    def test_pv_number_must_match_dp(self):
        self.pair()
        self.put("src/dp1_choice/pv2_wrong.py", "")
        code, out = self.run_cli()
        self.assertEqual(code, 1, out)
        self.assertIn("number", out)

    def test_pv_files_can_share_a_label(self):
        self.pair()
        for name in ("pv1_impl.h", "pv1_impl.c", "pv1_impl.test.ts", "dp1_choice.go"):
            self.put(f"src/dp1_choice/{name}", "")
        code, out = self.run_cli("--spec", str(self.model()))
        self.assertEqual(code, 0, out)

    def test_model_pv_alias_must_match_realized_dp(self):
        self.pair()
        spec = self.model()
        spec.write_text(spec.read_text().replace('alias = "PV1"', 'alias = "PV2"'))
        code, out = self.run_cli("--spec", str(spec))
        self.assertEqual(code, 1, out)
        self.assertIn("PV2", out)

    def test_multiple_pvs_can_realize_one_active_dp(self):
        self.pair()
        self.put("src/dp1_choice/pv1_adapter.py", "pass")
        spec = self.model('''pv "adapter" {
alias = "PV1"
realizes = [dp.choice]
}
''')
        code, out = self.run_cli("--spec", str(spec))
        self.assertEqual(code, 0, out)

    def test_inactive_branch_does_not_need_numbered_layout_aliases(self):
        self.pair()
        spec = self.model('''fr "unused" {
statement = "Inactive child outcome"
parent = dp.unused_choice
}
dp "unused_choice" {
controls = [fr.outcome]
decision = "rejected"
responsibility = "Rejected alternative"
}
pv "unused_impl" {
realizes = [dp.unused_choice]
}
''')
        code, out = self.run_cli("--spec", str(spec))
        self.assertEqual(code, 0, out)

    def test_duplicate_aliases_and_labels_fail(self):
        self.pair()
        for extra in ('fr "again" { alias = "FR1"\nstatement = "Another outcome" }',
                      'fr "outcome" { alias = "FR2"\nstatement = "Another outcome" }'):
            with self.subTest(extra=extra):
                code, out = self.run_cli("--spec", str(self.model(extra)))
                self.assertEqual(code, 1, out)
                self.assertIn("duplicate", out.lower())

    def two_branches(self):
        first = self.pair()
        self.put("src/dp2_other_choice/pv2_other_impl.py", "pass\n")
        self.put("tests/fr2_other/scenario.py", "dp2_other_choice")
        return first

    def test_conditional_zero_beside_reference_fails_only_under_policy(self):
        first = self.two_branches()
        self.put("src/dp2_other_choice/use.py", first)
        spec = self.model('''context "wet" { description = "Wet conditions" }
influence {
from = [dp.choice]
to = fr.other
effect = "none"
because = "Conditional isolation"
under = context.wet
}
influence {
from = [dp.choice]
to = fr.other
effect = "unknown"
}
''', second=True)
        code, out = self.run_cli("--spec", str(spec))
        self.assertEqual(code, 0, out)
        self.assertIn("REVIEW WARNING", out)
        self.assertIn("context.wet", out)
        code, out = self.run_cli("--spec", str(spec), "--expect", "decoupled")
        self.assertEqual(code, 1, out)
        self.assertIn("violates --expect decoupled", out)

    def test_reference_counts_for_ancestor_cells(self):
        self.two_branches()
        self.put("src/dp1_choice/dp1_1_child_choice/pv1_1_child_impl.py", "pass\n")
        self.put("tests/fr1_outcome/fr1_1_child/scenario.py", "dp1_1_child_choice")
        self.put("src/dp2_other_choice/use.py", "dp1_1_child_choice")
        spec = self.model('''fr "child" {
alias = "FR1.1"
statement = "Child outcome"
parent = dp.choice
}
dp "child_choice" {
alias = "DP1.1"
controls = [fr.child]
decision = "selected"
responsibility = "Control the child outcome"
}
pv "child_impl" {
alias = "PV1.1"
realizes = [dp.child_choice]
}
influence {
from = [dp.choice]
to = fr.other
effect = "none"
because = "The branches share nothing"
}
''', second=True)
        code, out = self.run_cli("--spec", str(spec))
        self.assertEqual(code, 0, out)
        self.assertIn("zero for FR2 <- DP1 ", out)

    def test_cells_default_counts_as_zero_claim(self):
        first = self.two_branches()
        self.put("src/dp2_other_choice/use.py", first)
        spec = self.model('cells "defaults" {\nscope = design.demo\nunlisted = "none"\n'
                          'because = "Siblings share nothing"\n}\n', second=True)
        code, out = self.run_cli("--spec", str(spec), "--expect", "decoupled")
        self.assertEqual(code, 1, out)
        self.assertIn("zero for FR2 <- DP1 ", out)

    def test_reference_without_model_record_is_reported(self):
        first = self.two_branches()
        self.put("src/dp2_other_choice/use.py", first)
        code, out = self.run_cli("--spec", str(self.model(second=True)))
        self.assertEqual(code, 0, out)
        self.assertIn("no influence record for FR2 <- DP1", out)

    def test_coupling_and_loop_blocks_are_read(self):
        self.pair()
        spec = self.model('''coupling "cycle" {
scope = design.demo
affects = [fr.outcome]
reason = "Shared timing"
}
module "runner" {
realizes = [dp.choice]
}
flow "run" {
steps = [module.runner]
loop {
after = module.runner
back_to = module.runner
when = "retry"
bound = 3
}
}
''')
        code, out = self.run_cli("--spec", str(spec))
        self.assertEqual(code, 0, out)
        self.assertIn("coupling", out)

    def test_source_root_file_composes_top_level_only(self):
        self.pair()
        self.pair("1_1", "child", "child", "dp1_choice/", "fr1_outcome/")
        lib = self.put("src/lib.rs", "mod dp1_choice;\n")
        code, out = self.run_cli()
        self.assertEqual(code, 0, out)
        lib.write_text("use dp1_1_child;\n", encoding="utf-8")
        code, out = self.run_cli()
        self.assertEqual(code, 1, out)
        self.assertIn("composition root names nested", out)

    def test_comments_and_strings_are_not_model_references(self):
        self.pair()
        extra = '''influence {
from = [dp.choice] # dp.missing
# to = fr.missing
to = fr.outcome
effect = "material"
mechanism = "A literal dp.missing and fr.missing"
}
'''
        code, out = self.run_cli("--spec", str(self.model(extra)))
        self.assertEqual(code, 0, out)

    def test_partial_or_unsupported_model_input_fails(self):
        self.pair()
        for text in ("", 'fr "broken" { alias = "FR1"',
                     'garbage\n', 'project "demo" { core = [] }',
                     'fr "bad" { alias = <<EOF\nFR1\nEOF\n}',
                     'cells "defaults" { effect = "none" }',
                     'fr "bad" { alias = "FR1" alias = "FR2" }',
                     'fr "bad" { alias = "${dp.choice}" }'):
            with self.subTest(text=text):
                spec = self.put("spec/bad.ad.hcl", text)
                code, out = self.run_cli("--spec", str(spec))
                self.assertEqual(code, 1, out)
                self.assertIn("spec", out.lower())

    def test_manifest_and_empty_directory_are_rejected(self):
        self.pair()
        manifest = self.put("only/project.ad.project.hcl", 'project "demo" {}')
        for path in (manifest, manifest.parent):
            with self.subTest(path=path):
                code, out = self.run_cli("--spec", str(path))
                self.assertEqual(code, 1, out)
                self.assertIn("spec", out.lower())

    def test_unknown_source_tokens_fail(self):
        self.pair()
        for token in ("dp9_missing", "dp1_old_label"):
            with self.subTest(token=token):
                self.put("src/dp1_choice/use.py", token)
                code, out = self.run_cli()
                self.assertEqual(code, 1, out)
                self.assertIn("unknown DP token", out)

    def test_literal_objects_parse_but_duplicate_keys_fail(self):
        self.pair()
        for fields, success in (("min = 0, max = 10", True),
                                ("min = 0, min = 10", False)):
            with self.subTest(fields=fields):
                spec = self.model('workload "load" {\ndescription = "Input range"\n'
                                  'ranges = { rate = { ' + fields + ' } }\n}\n')
                code, out = self.run_cli("--spec", str(spec))
                self.assertEqual(code, 0 if success else 1, out)
                if not success:
                    self.assertIn("duplicate object key", out)

    def test_expect_declaration_is_not_executed(self):
        self.pair()
        spec = self.model('expect "claim" {\nscope = design.demo\n'
                          'classification = "coupled"\n}\n')
        code, out = self.run_cli("--spec", str(spec))
        self.assertEqual(code, 0, out)
        self.assertIn("did not assess these block kinds: expect", out)

    def test_selected_dp_under_inactive_parent_fails(self):
        self.pair()
        extra = '''fr "child" {
alias = "FR1.1"
statement = "Child outcome"
parent = dp.choice
}
dp "child_choice" {
alias = "DP1.1"
controls = [fr.child]
decision = "selected"
responsibility = "Control child outcome"
}
'''
        spec = self.model(extra)
        text = spec.read_text().replace('decision = "selected"', 'decision = "rejected"', 1)
        spec.write_text(text)
        code, out = self.run_cli("--spec", str(spec))
        self.assertEqual(code, 1, out)
        self.assertIn("active FR", out)

    def test_symlink_root_is_not_scanned(self):
        self.pair()
        link = self.root / "linked"
        link.symlink_to(self.root, target_is_directory=True)
        code, out = self.run_cli("--root", str(link))
        self.assertEqual(code, 1, out)
        self.assertIn("skipped symlink", out)


if __name__ == "__main__":
    unittest.main()
