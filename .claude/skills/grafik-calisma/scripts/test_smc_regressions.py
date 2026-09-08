"""Causal geometry, evidence lifecycle, and conditional-plan regressions."""
import copy
import unittest

import numpy as np
import pandas as pd

import confluence as cf
import smc_tespit as st


def bars(moves, start=100.):
    result = []
    for move in moves:
        close = start + move
        result.append(dict(open=start, high=max(start, close) + (.2 if move >= 0 else .1),
                           low=min(start, close) - (.1 if move >= 0 else .2), close=close))
        start = close
    return result


def timed(candles):
    return [dict(c, open_time=1_700_000_040_000 + i * 60_000,
                 close_time=1_700_000_099_999 + i * 60_000, closed=True)
            for i, c in enumerate(candles)]


def valid_job():
    return dict(structure=dict(event='CHoCH', direction='bull', confirmed=True,
                               age_bars=0, family_id='event:30'),
                impulse=dict(start=100., end=120.),
                order_blocks=[dict(id='ob:20', low=104.5, high=105., type='demand',
                                   status='fresh', family_id='event:20')],
                liquidity=[dict(price=125., type='buyside', status='open')],
                time_contract=dict(status='verified'),
                setup_lifecycle=dict(status='active'),
                confirmation=dict(confirmed=True, direction='bull', age_bars=0,
                                  level=104.75, kind='rejection'),
                current_price=105.2)


class SmcRegressions(unittest.TestCase):
    def test_wilder_sma_seed(self):
        df = pd.DataFrame([dict(open=100., high=100+w/2, low=100-w/2, close=100.)
                           for w in [1., 2., 3., 4.]])
        np.testing.assert_allclose(st.wilder_atr(df, 3).iloc[2:], [2., 8/3])

    def test_swept_liquidity_is_history_not_target(self):
        out = st.detect({'candles': bars([1.]*5 + [-1.]*5 + [1.]*5 + [-1.]*5 + [2.]*3)})
        self.assertNotIn(105.2, [q['price'] for q in out['likidite']])
        swept = [q for q in out['liquidity_all'] if q['price'] == 105.2]
        self.assertTrue(swept)
        self.assertEqual(swept[0]['status'], 'swept')
        self.assertIsNotNone(swept[0]['swept_i'])

    def test_invalidated_ob_not_active(self):
        out = st.detect({'candles': bars(([1.]*10 + [-1.]*7)*3 + [-20.] + [0.]*3)})
        self.assertFalse(any(o['type'] == 'demand' for o in out['order_blocks']))
        self.assertTrue(any(o['status'] == 'invalidated' for o in out['order_blocks_all']))

    def test_cutoff_excludes_future_and_open_candles(self):
        candles = timed(bars(([1.]*10 + [-1.]*7)*2))
        cutoff = candles[-1]['close_time']
        later = dict(candles[-1], open_time=cutoff+1, close_time=cutoff+60_000,
                     high=150., close=149., closed=False)
        a = st.detect(dict(candles=candles, cutoff=cutoff))
        b = st.detect(dict(candles=candles+[later], cutoff=cutoff))
        self.assertEqual(a['confluence_job'], b['confluence_job'])
        self.assertEqual(b['bar_sayisi'], len(candles))
        self.assertEqual(b['normalized_candles'][-1]['source_i'], len(candles)-1)
        self.assertEqual(b['time_contract']['status'], 'verified')

    def test_cutoff_requires_closing_time(self):
        candles = [dict(c, timestamp=1020+i*60, closed=True)
                   for i, c in enumerate(bars([1.]*25))]
        with self.assertRaises(st.TespitError):
            st.load_frame(dict(candles=candles, cutoff=3000))
        self.assertEqual(len(st.load_frame(dict(candles=candles, cutoff=3000,
                                                interval_seconds=60))), 25)

    def test_cutoff_alias_typo_is_rejected(self):
        with self.assertRaises(st.TespitError):
            st.load_frame(dict(candles=bars([1.]*25), c0_timestamp=1234))

    def test_declared_timeframe_cannot_close_early(self):
        origin = 1_700_000_000_000 // 14_400_000 * 14_400_000
        candles = [dict(c, open_time=origin+i*14_400_000,
                        close_time=origin+i*14_400_000+900_000-1, closed=True)
                   for i, c in enumerate(bars([1.]*25))]
        with self.assertRaisesRegex(st.TespitError, 'close_time'):
            st.load_frame(dict(candles=candles, cutoff=candles[-1]['close_time'], timeframe='4h'))

    def test_declared_timeframe_rejects_misaligned_open(self):
        candles = timed(bars([1.]*25))
        for c in candles:
            c['open_time'] += 1
            c['close_time'] += 1
        with self.assertRaisesRegex(st.TespitError, 'ızgarasına'):
            st.load_frame(dict(candles=candles, cutoff=candles[-1]['close_time'], timeframe='1m'))

    def test_timeframe_and_interval_must_agree(self):
        candles = timed(bars([1.]*25))
        with self.assertRaisesRegex(st.TespitError, 'timeframe ile interval_seconds'):
            st.normalize_candles(candles, dict(timeframe='4h', interval_seconds=900,
                                               cutoff=candles[-1]['close_time']))

    def test_htf_timeframe_and_interval_must_agree(self):
        candles = timed(bars([1.]*25))
        with self.assertRaisesRegex(st.TespitError, 'timeframe ile interval_seconds'):
            st.detect(dict(candles=candles, timeframe='1m', interval_seconds=60,
                           cutoff=candles[-1]['close_time'], htf_candles=candles,
                           htf_timeframe='4h', htf_interval_seconds=900))

    def test_binance_arrays_and_records_normalize_identically(self):
        candles = timed(bars([1.]*25))
        arrays = [[c['open_time'], c['open'], c['high'], c['low'], c['close'], 1.,
                   c['close_time'], 1., 1, 0., 0., '0'] for c in candles]
        frame = st.load_frame(dict(candles=arrays, timeframe='1m', cutoff=candles[-1]['close_time']))
        self.assertEqual(frame.attrs['time_contract']['status'], 'verified')
        self.assertEqual(frame.iloc[-1].open_time_ms, candles[-1]['open_time'])

    def test_bad_ohlc_is_rejected_not_dropped(self):
        data = bars([1.]*25)
        data[7]['close'] = float('nan')
        with self.assertRaises(st.TespitError):
            st.load_frame(dict(candles=data))

    def test_untimed_is_explicit_and_candidates_not_confirmed(self):
        out = st.detect(dict(candles=bars([1.]*22 + [-1.])))
        self.assertEqual(out['time_contract']['status'], 'time_unverified')
        self.assertTrue(out['swings']['candidates'])
        self.assertTrue(all(not s['confirmed'] for s in out['swings']['candidates']))

    def test_structure_prefix_consistency(self):
        data = pd.DataFrame(bars(([1.]*10 + [-1.]*7)*5))
        hi, lo = st.find_swings(data)
        _, full = st.structure_events(data, hi, lo)
        for end in range(20, len(data)+1):
            prefix = data.iloc[:end]
            h, l = st.find_swings(prefix)
            _, events = st.structure_events(prefix, h, l)
            self.assertEqual(events, [e for e in full if e['i'] < end])

    def test_fvg_midpoint_consumption_preserves_partial_geometry(self):
        data = pd.DataFrame([dict(open=100, high=101, low=99, close=100.5),
            dict(open=100.5, high=103, low=100.4, close=102.8),
            dict(open=102.8, high=104, low=102.2, close=103.5),
            dict(open=103.5, high=103.6, low=101.4, close=101.5)])
        fvg = st.find_fvgs(data)[0]
        self.assertTrue(fvg['dolu'])
        self.assertEqual(fvg['fill_status'], 'partial')
        self.assertLess(fvg['fill_ratio'], 1.)

    def test_order_block_partial_and_consumed_are_distinct(self):
        base = [dict(open=102., high=103., low=99., close=100.),
                dict(open=100., high=106., low=99.5, close=105.),
                dict(open=105., high=111., low=104., close=110.)]
        event = dict(impulse_start_i=0, i=2, direction='bull')
        for low, status, available in [(102., 'mitigated', True), (101., 'consumed', False)]:
            frame = pd.DataFrame(base + [dict(open=110., high=110., low=low, close=104.)])
            ob = st.find_order_block(frame, event)
            self.assertEqual(ob['status'], status)
            self.assertEqual(ob['entry_available'], available)


class ConfluenceRegressions(unittest.TestCase):
    def test_valid_confirmed_plan_remains_usable(self):
        out = cf.synth(valid_job())
        self.assertEqual(out['KARAR'], 'LONG')
        self.assertTrue(out['executable'])
        self.assertEqual(out['hedefler'], [125.])

    def test_disjoint_zone_cannot_flip_decision(self):
        job = valid_job()
        job['fvgs'] = [dict(low=107., high=107.5, type='bull', status='fresh')]
        job['thresholds'] = dict(min_confluence=.8)
        out = cf.synth(job)
        self.assertEqual(out['KARAR'], 'NÖTR-BEKLE')
        self.assertLess(out['confluence_skoru'], .8)

    def test_missing_target_is_not_invented(self):
        job = valid_job()
        job['liquidity'] = []
        out = cf.synth(job)
        self.assertEqual(out['KARAR'], 'NÖTR-BEKLE')
        self.assertEqual(out['hedefler'], [])
        self.assertFalse(out['executable'])
        self.assertEqual(out['plan_yonu'], 'LONG')

    def test_stale_or_unconfirmed_trigger_is_draft(self):
        for field, value in [('age_bars', 15), ('confirmed', False)]:
            job = valid_job()
            job['confirmation'][field] = value
            out = cf.synth(job)
            self.assertFalse(out['executable'])
            self.assertEqual(out['plan_yonu'], 'LONG')

    def test_old_active_structure_with_new_retest_remains_usable(self):
        job = valid_job()
        job['structure']['age_bars'] = 15
        self.assertTrue(cf.synth(job)['executable'])

    def test_target_behind_current_price_is_not_open(self):
        job = valid_job()
        job['current_price'] = 130.
        self.assertEqual(cf.synth(job)['hedefler'], [])

    def test_paid_setup_cannot_reuse_fresh_trigger(self):
        job = valid_job()
        job['setup_lifecycle'] = dict(status='completed', target_paid=True)
        self.assertFalse(cf.synth(job)['executable'])

    def test_missing_timing_or_confirmation_is_draft(self):
        for missing in ('time_contract', 'confirmation'):
            job = valid_job()
            job.pop(missing)
            out = cf.synth(job)
            self.assertFalse(out['executable'])
            self.assertEqual(out['plan_yonu'], 'LONG')
            self.assertIsNone(out['first_leg']['direction'])

    def test_invalidated_zone_and_swept_target_are_ignored(self):
        for key, status in [('order_blocks', 'invalidated'), ('liquidity', 'swept')]:
            job = valid_job()
            job[key][0]['status'] = status
            self.assertFalse(cf.synth(job)['executable'])

    def test_same_event_family_is_not_counted_twice(self):
        job = valid_job()
        job['order_blocks'][0]['family_id'] = job['structure']['family_id']
        job['fvgs'] = [dict(id='fvg:30', low=104.6, high=104.9, type='bull',
                            status='fresh', family_id=job['structure']['family_id'])]
        out = cf.synth(job)
        self.assertLessEqual(out['confluence_skoru'], .45)

    def test_nonfinite_threshold_is_rejected(self):
        job = valid_job()
        job['thresholds'] = dict(min_rr=float('nan'))
        with self.assertRaises(cf.ConfluenceError):
            cf.synth(job)

    def test_negative_derived_stop_is_rejected(self):
        job = valid_job()
        job['atr'] = 200.
        job['liquidity'][0]['price'] = 1000.
        with self.assertRaisesRegex(cf.ConfluenceError, 'giriş/stop geometrisi'):
            cf.synth(job)

    def test_nonpositive_input_price_is_rejected(self):
        job = valid_job()
        job['impulse']['start'] = 0.
        with self.assertRaisesRegex(cf.ConfluenceError, 'pozitif'):
            cf.synth(job)

    def test_small_price_geometry_survives_output_precision(self):
        job = valid_job()
        scale = 1e-10
        for key in ('start', 'end'):
            job['impulse'][key] *= scale
        for key in ('low', 'high'):
            job['order_blocks'][0][key] *= scale
        job['liquidity'][0]['price'] *= scale
        job['confirmation']['level'] *= scale
        job['current_price'] *= scale
        out = cf.synth(job)
        self.assertTrue(out['executable'])
        self.assertTrue(0 < out['gecersizlik_sl'] < out['giris_bolgesi'][0]
                        < out['giris_orta'] < out['giris_bolgesi'][1] < out['hedefler'][0])


if __name__ == '__main__':
    unittest.main()
