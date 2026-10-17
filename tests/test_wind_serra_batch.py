import importlib.util, tempfile, unittest, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("wind_serra_batch",ROOT/"scripts/wind_serra_batch.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class WindSerraBatch(unittest.TestCase):
    def test_seed_previous_eight_without_download(self):
        state={"documents":{}}
        mod.seed(state)
        self.assertEqual(len(state["documents"]),8)
        self.assertTrue(all(v["status"]=="prior_reviewed" for v in state["documents"].values()))
        self.assertTrue(all(len(v["sha256"])==64 for v in state["documents"].values()))
    def test_rank_priority_is_2026_and_timeline(self):
        rows=[{"title":"Studio vegetazione","filename":"s.pdf","published":"24/03/2026"},
              {"title":"Cronoprogramma BoP","filename":"a.pdf","published":"24/03/2026"},
              {"title":"Cronoprogramma storico","filename":"b.pdf","published":"24/03/2019"}]
        self.assertEqual(sorted(rows,key=mod.score)[0]["title"],"Cronoprogramma BoP")
    def test_candidates_keep_page_and_not_confirmed(self):
        d={"pages":[{"page":7,"text":"RWE committente, contratto BoP. Avvio lavori 2027.","visual_review_needed":False}]}
        found,visual=mod.excerpt(d)
        self.assertEqual(found["roles"][0]["page"],7)
        self.assertIn("timeline",found)
        self.assertEqual(visual,[])
    def test_offline_restart_zero_network_and_no_new_facts(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/"state.json"
            report=Path(d)/"report.json"
            state.write_text(json.dumps({"project_id":"serra-giannina","inventory":{},
                                         "documents":{}}),encoding="utf8")
            obj=mod.run(state,report,offline=True)
            self.assertEqual(obj["network"],{})
            self.assertEqual(obj["batch"],[])
            self.assertEqual(obj["new_verified_facts"],0)
            self.assertFalse(obj["dossier_complete"])
            self.assertEqual(obj["prior_reviewed"],8)

if __name__=="__main__":unittest.main()
