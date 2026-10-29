import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import datetime as dt
import unittest
import xml.etree.ElementTree as ET
from activity_cards import collect_year, streaks, render


class ActivityTests(unittest.TestCase):
    def test_true_event_types_and_utc_dates(self):
        now=dt.datetime(2026,10,29,15,tzinfo=dt.timezone.utc)
        def api(path):
            return {'Python': 120, 'HTML': 80} if path.endswith('/languages') else {'private':False,'default_branch':'main','has_issues':True}
        def pages(path,**kwargs):
            if '/commits?' in path:
                return iter([{'commit':{'committer':{'date':'2026-10-29T01:00:00Z'}}}])
            if '/issues?' in path:
                return iter([{'created_at':'2026-10-28T01:00:00Z'}, {'created_at':'2026-10-28T02:00:00Z','pull_request':{} }])
            if '/pulls?' in path:
                return iter([{'created_at':'2025-01-01T00:00:00Z','updated_at':'2026-10-29T00:00:00Z','number':1}])
            if '/reviews' in path:
                return iter([{'state':'APPROVED','submitted_at':'2026-10-29T00:00:00Z'}, {'state':'PENDING','submitted_at':None}])
            raise AssertionError(path)
        a=collect_year(now,[{'name':'app'}],api,pages,'test')
        self.assertEqual(a['kinds'],{'Commits':1,'Issues':1,'Pull requests':0,'Reviews':1})
        self.assertEqual(sum(a['daily'].values()),3)
        self.assertEqual(a['daily']['2026-10-29'],2)
        self.assertEqual(len(a['daily']),365)
        self.assertEqual(a['languages']['Python'],120)
        ET.fromstring(render({'activity':a,'repos':[{'name':'app'}],'updated':'2026-10-29T15:00:00Z'}).svg())

    def test_streak_grace_for_today(self):
        daily={'2026-10-26':2,'2026-10-27':1,'2026-10-28':2,'2026-10-29':0}
        self.assertEqual(streaks(daily,'2026-10-29'),(3,3))
        self.assertEqual(streaks(daily,'2026-10-30'),(0,3))

    def test_private_visibility_change_stops_collection(self):
        with self.assertRaises(RuntimeError):
            collect_year(dt.datetime.now(dt.timezone.utc),[{'name':'app'}],lambda _: {'private':True},lambda _: [],'test')
