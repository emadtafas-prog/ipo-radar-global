import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scanner import (parse_sec_atom,parse_finnhub_ipos,parse_euronext,parse_lse,
                     parse_news_rss,iso_date,run,region_of_exchange,send_app_push)

class GlobalScannerTests(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(iso_date('26/10/2026'),'2026-10-26')
        self.assertEqual(iso_date('2026-10-23T10:20:03Z'),'2026-10-23')
        self.assertEqual(iso_date('26 October 2026'),'2026-10-26')
        self.assertEqual(iso_date('Late October 2026'),'')
    def test_sec_is_registration_not_listing(self):
        xml='''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>urn:sec:test:123</id><title>S-1 - Acme Biotech, Inc. (0001234567) (Filer)</title><updated>2026-10-23T17:00:00Z</updated><link href="https://www.sec.gov/Archives/edgar/data/123/" /></entry></feed>'''
        rows=parse_sec_atom(xml,'S-1')
        self.assertEqual(rows[0]['name'],'Acme Biotech, Inc.')
        self.assertEqual(rows[0]['status'],'registration')
        self.assertEqual(rows[0]['confidence'],'official')
        self.assertEqual(rows[0]['type'],'filing')
    def test_exchange_region(self):
        self.assertEqual(region_of_exchange('NYSE')[0],'US')
        self.assertEqual(region_of_exchange('LSE AIM')[0],'UK')
        self.assertEqual(region_of_exchange('Euronext Paris')[0],'EU')
        self.assertEqual(region_of_exchange('BSE')[0],'IN')
    def test_finnhub_calendar_is_estimate(self):
        r=parse_finnhub_ipos({'ipoCalendar':[{'name':'Acme','symbol':'ACM','date':'2026-11-01','status':'expected','exchange':'NASDAQ','priceLow':10,'priceHigh':13}]})
        self.assertEqual(r[0]['price_range'],'10–13 USD')
        self.assertEqual(r[0]['confidence'],'calendar')
        self.assertEqual(r[0]['region'],'US')
    def test_euronext_coming_and_recent(self):
        html='''<h2>Recent IPOs</h2><ul><li>05/10/2026</li><li>Volare Shipping Ltd.</li><li>Oslo</li><li>Euronext Growth</li></ul>
        <h2>Coming IPOs</h2><ul><li>26/10/2026</li><li>N4 GROUP S.A</li><li>Paris</li></ul>
        <h2>Athens</h2><div>For new listings</div>'''
        rows=parse_euronext(html)
        self.assertEqual(len(rows),2)
        self.assertEqual({r['status'] for r in rows},{'listed','expected'})
        self.assertTrue(all(r['region']=='EU' for r in rows))
    def test_lse_filters_out_bonds(self):
        html='''<h2>Upcoming issues</h2><table><thead><tr><th>Name</th><th>Market</th><th>Expected size of primary offer</th><th>Expected size of secondary offer</th><th>Currency</th><th>Price range</th><th>Expected first date of trading</th><th>Type</th></tr></thead><tbody>
        <tr><td><a href="/stock/abc">Alpha Ventures</a></td><td>AIM</td><td>TBC</td><td>-</td><td>GBP</td><td>-</td><td>26 October 2026</td><td>Equity</td></tr>
        <tr><td>Bank Bond</td><td>MAIN</td><td>-</td><td>-</td><td>USD</td><td>-</td><td>26 October 2026</td><td>Bonds</td></tr></tbody></table>'''
        rows=parse_lse(html)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['name'],'Alpha Ventures')
        self.assertEqual(rows[0]['date'],'2026-10-26')
        self.assertEqual(rows[0]['region'],'UK')
    def test_news_not_official(self):
        feed='''<rss version="2.0"><channel><item><title>Example Company files IPO in India</title><link>https://news.google.com/articles/test</link><pubDate>Sat, 24 Oct 2026 12:00:00 GMT</pubDate><source>News Site</source></item><item><title>Football news</title><link>https://example.com</link><pubDate>Sat, 24 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'''
        result=parse_news_rss(feed,'الهند','IN',now=datetime(2026,10,25,tzinfo=timezone.utc))
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['type'],'news')
        self.assertEqual(result[0]['status'],'reported')
        self.assertEqual(result[0]['confidence'],'news')
    def test_deduplication_and_history_on_feed_failure(self):
        item={'key':'test:one','name':'Real Example','type':'ipo','status':'expected','date':'2026-11-03','source':'Example','source_url':'https://example.com','region':'EU','region_label':'أوروبا','confidence':'official'}
        now=datetime(2026,10,25,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'signals.json'
            source=[('exchange','official','EU',lambda:[item])]
            first=run(now=now,data_path=path,collectors=source)
            self.assertEqual(first['items'][0]['name'],'Real Example')
            self.assertTrue(first['generated_at'])
            self.assertEqual(len(first['seen_keys']),1)
            prior_seen=first['items'][0]['last_seen_at']
            def raise_err():raise RuntimeError('unavailable')
            second=run(now=now.replace(day=26),data_path=path,collectors=[('exchange','official','EU',raise_err)])
            self.assertEqual(len(second['items']),1)
            self.assertEqual(second['items'][0]['last_seen_at'],prior_seen)
            self.assertEqual(second['source_status'][0]['status'],'error')

    def test_notification_inbox_only_after_first_scan_and_not_repeated(self):
        now=datetime(2026,10,25,tzinfo=timezone.utc)
        company={'key':'official:alpha','name':'Alpha Bio','type':'ipo','status':'expected',
                 'date':'2026-11-03','source':'Exchange','source_url':'https://example.com/alpha',
                 'region':'EU','region_label':'أوروبا','confidence':'official'}
        filing={**company,'key':'filing:beta','name':'Beta Labs','type':'filing','status':'registration'}
        news={**company,'key':'news:gamma','name':'Rumour','type':'news','confidence':'news'}
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'signals.json'
            collectors=[('exchange','official','EU',lambda:[company,news])]
            first=run(now=now,data_path=path,collectors=collectors)
            self.assertEqual(first['alerts'],[])
            second=run(now=now.replace(day=26),data_path=path,collectors=[('exchange','official','EU',lambda:[company,news,filing])])
            self.assertEqual(len(second['alerts']),1)
            self.assertEqual(second['alerts'][0]['kind'],'filing')
            third=run(now=now.replace(day=27),data_path=path,collectors=[('exchange','official','EU',lambda:[company,news,filing])])
            self.assertEqual(len(third['alerts']),1)
            self.assertNotIn('news:gamma',[a['key'] for a in third['alerts']])

    @patch('scanner.requests.post')
    def test_push_api_payload_and_idempotency(self,post):
        post.return_value.json.return_value={'id':'test-notification-id'}
        post.return_value.raise_for_status.return_value=None
        entries=[{'key':'ipo:alpha','company':'Example Plc'}]
        success=send_app_push('app-id','VERY_SECRET_KEY',entries,'https://example.com/ipo-radar-global/')
        self.assertTrue(success)
        self.assertEqual(post.call_args.args[0],'https://api.onesignal.com/notifications')
        payload=post.call_args.kwargs['json']
        self.assertEqual(payload['target_channel'],'push')
        self.assertEqual(payload['web_url'],'https://example.com/ipo-radar-global/#alertsPanel')
        self.assertNotIn('VERY_SECRET_KEY',str(payload))
        self.assertEqual(payload['idempotency_key'],payload['idempotency_key'])

if __name__=='__main__': unittest.main()
