from __future__ import annotations
import traceback
import streamlit as st
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from src.services.valuation_service import ValuationService, ValuationParams


def _get_service():
    return ValuationService()


def _fetch_case(case_id):
    return _get_service().get_case(case_id)


def _build_params(p, case_name=''):
    return ValuationParams(
        case_name      = case_name or p.get('case_name', ''),
        stock_price    = float(p.get('stock_price',    100)),
        strike_price   = float(p.get('strike_price',   100)),
        risk_free_rate = float(p.get('risk_free_rate', 0.02)),
        volatility     = float(p.get('volatility',     0.30)),
        time_to_expiry = float(p.get('time_to_expiry', 1.0)),
        option_type    = p.get('option_type', 'call'),
        dividend_yield = float(p.get('dividend_yield', 0.0)),
        binomial_steps = int(p.get('binomial_steps',   100)),
        mc_simulations = int(p.get('mc_simulations',   10000)),
    )


def _plot_mc_histogram(payoffs, price):
    arr = np.array(payoffs, dtype=float)
    fig, ax = plt.subplots(figsize=(7, 3))
    ax.hist(arr, bins=60, color='#4C8BF5', edgecolor='white', alpha=0.85)
    ax.axvline(price, color='red', linewidth=1.8, linestyle='--',
               label='MC Price: {:.2f}'.format(price))
    ax.set_xlabel('Payoff')
    ax.set_ylabel('Frequency')
    ax.set_title('Monte Carlo Payoff Distribution')
    ax.legend()
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _fmt(v):
    if isinstance(v, float): return '{:.6f}'.format(v)
    if isinstance(v, int):   return '{:,}'.format(v)
    if isinstance(v, list):
        preview = ['{:.4f}'.format(x) if isinstance(x, float) else str(x)
                   for x in v[:4]]
        tail = ' ...' if len(v) > 4 else ''
        return '[' + ', '.join(preview) + tail + ']'
    return str(v)


def _show_scalars(d, skip=('ST_hist', 'payoff_hist')):
    items = [(k, v) for k, v in d.items()
             if k not in skip and not isinstance(v, list)]
    if not items:
        st.info('No data.')
        return
    cols = st.columns(3)
    for idx, (k, v) in enumerate(items):
        cols[idx % 3].metric(k, _fmt(v))


def _show_list_items(d, skip=('ST_hist', 'payoff_hist')):
    for k, v in d.items():
        if k not in skip and isinstance(v, list):
            with st.expander('- ' + k + ' (' + str(len(v)) + ' items)',
                             expanded=False):
                st.write(v)


def _init_edit_state(case, case_id):
    if st.session_state.get('_edit_case_id') != case_id:
        st.session_state['_edit_case_id']     = case_id
        st.session_state['edit_case_name']    = case.get('case_name', '')
        st.session_state['edit_stock_price']  = float(case.get('stock_price',    100))
        st.session_state['edit_strike']       = float(case.get('strike_price',   100))
        st.session_state['edit_rate']         = float(case.get('risk_free_rate', 0.02))
        st.session_state['edit_div']          = float(case.get('dividend_yield', 0.0))
        st.session_state['edit_vol']          = float(case.get('volatility',     0.30))
        st.session_state['edit_tte']          = float(case.get('time_to_expiry', 1.0))
        st.session_state['edit_opt_type']     = case.get('option_type', 'call')
        st.session_state['edit_bin_steps']    = int(case.get('binomial_steps',   100))
        st.session_state['edit_mc_sims']      = int(case.get('mc_simulations',   10000))
        st.session_state['edit_result']       = None
        st.session_state['edit_result_dirty'] = True


def _read_edit_state():
    return dict(
        case_name      = st.session_state.get('edit_case_name',   ''),
        stock_price    = st.session_state.get('edit_stock_price', 100.0),
        strike_price   = st.session_state.get('edit_strike',      100.0),
        risk_free_rate = st.session_state.get('edit_rate',        0.02),
        volatility     = st.session_state.get('edit_vol',         0.30),
        time_to_expiry = st.session_state.get('edit_tte',         1.0),
        option_type    = st.session_state.get('edit_opt_type',    'call'),
        dividend_yield = st.session_state.get('edit_div',         0.0),
        binomial_steps = st.session_state.get('edit_bin_steps',   100),
        mc_simulations = st.session_state.get('edit_mc_sims',     10000),
    )


def _show_comparable_vol_selector(case_id):
    svc = _get_service()
    try:
        tickers = svc.get_comparable_tickers(case_id)
    except Exception:
        tickers = []
    if not tickers:
        return
    st.markdown('---')
    st.markdown('**Comparable Company Volatility**')
    rows = []
    for t in tickers:
        vol = t.get('volatility') or t.get('vol')
        if vol is not None:
            rows.append({
                'ticker':     t.get('ticker', ''),
                'company':    t.get('company_label') or t.get('ticker', ''),
                'volatility': float(vol),
            })
    if not rows:
        st.caption('No comparable companies with volatility data.')
        return
    cols = st.columns([2, 2, 2, 1])
    cols[0].markdown('**Ticker**')
    cols[1].markdown('**Company**')
    cols[2].markdown('**Volatility**')
    cols[3].markdown('**Apply**')
    for row in rows:
        c0, c1, c2, c3 = st.columns([2, 2, 2, 1])
        c0.write(row['ticker'])
        c1.write(row['company'])
        c2.write('{:.1%}'.format(row['volatility']))
        btn_key = 'apply_vol_' + row['ticker'] + '_' + str(case_id)
        if c3.button('Apply', key=btn_key):
            st.session_state['edit_vol'] = row['volatility']
            st.rerun()


def show():
    case_id = st.session_state.get('detail_case_id')
    if not case_id:
        st.warning('No case selected.')
        if st.button('Back to Home'):
            st.session_state['current_page'] = 'home'
            st.rerun()
        return
    case = _fetch_case(case_id)
    if not case:
        st.error('Case ID=' + str(case_id) + ' not found.')
        return
    _init_edit_state(case, case_id)
    st.title('Case Detail: ' + case.get('case_name', ''))
    tab_edit, tab_result, tab_mc = st.tabs(
        ['Edit Parameters', 'Valuation Results', 'MC Histogram']
    )
    with tab_edit:
        st.subheader('Edit Parameters')
        col1, col2 = st.columns(2)
        with col1:
            st.session_state['edit_case_name'] = st.text_input(
                'Case Name', value=st.session_state['edit_case_name'],
                key='_w_case_name')
            st.session_state['edit_stock_price'] = st.number_input(
                'Stock Price (S)', value=st.session_state['edit_stock_price'],
                step=1.0, key='_w_stock_price')
            st.session_state['edit_strike'] = st.number_input(
                'Strike Price (K)', value=st.session_state['edit_strike'],
                step=1.0, key='_w_strike')
            st.session_state['edit_rate'] = st.number_input(
                'Risk-Free Rate', value=st.session_state['edit_rate'],
                step=0.001, format='%.3f', key='_w_rate')
            st.session_state['edit_div'] = st.number_input(
                'Dividend Yield', value=st.session_state['edit_div'],
                step=0.001, format='%.3f', key='_w_div')
        with col2:
            new_vol = st.number_input(
                'Volatility', value=st.session_state['edit_vol'],
                step=0.01, format='%.3f', key='_w_vol')
            st.session_state['edit_vol'] = new_vol
            st.session_state['edit_tte'] = st.number_input(
                'Time to Expiry (T)', value=st.session_state['edit_tte'],
                step=0.1, format='%.2f', key='_w_tte')
            opt_options = ['call', 'put']
            opt_idx = 0 if st.session_state['edit_opt_type'] == 'call' else 1
            selected = st.selectbox(
                'Option Type', opt_options, index=opt_idx, key='_w_opt_type')
            st.session_state['edit_opt_type'] = selected
            st.session_state['edit_bin_steps'] = int(st.number_input(
                'Binomial Steps', value=st.session_state['edit_bin_steps'],
                step=10, min_value=10, key='_w_bin_steps'))
            st.session_state['edit_mc_sims'] = int(st.number_input(
                'MC Simulations', value=st.session_state['edit_mc_sims'],
                step=1000, min_value=1000, key='_w_mc_sims'))
        _show_comparable_vol_selector(case_id)
        st.divider()
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
        with btn_col1:
            calc_btn = st.button('Recalculate', type='primary',
                                 use_container_width=True)
        with btn_col2:
            save_btn = st.button('Save', use_container_width=True)
        with btn_col3:
            new_name_input = st.text_input(
                'Save As Name', value='', key='_w_new_name',
                label_visibility='collapsed', placeholder='New case name')
            saveas_btn = st.button('Save As', use_container_width=True)
        with btn_col4:
            del_btn = st.button('Delete', type='secondary',
                                use_container_width=True)
        edited = _read_edit_state()
        svc    = _get_service()
        if calc_btn:
            with st.spinner('Calculating...'):
                try:
                    params = _build_params(edited)
                    result = svc.calculate(params)
                    st.session_state['edit_result']       = result
                    st.session_state['edit_result_dirty'] = False
                    st.success('Recalculation complete.')
                except Exception as e:
                    st.error('Calculation error: ' + str(e))
                    st.code(traceback.format_exc())
        if save_btn:
            try:
                params = _build_params(edited)
                svc.update_case(case_id, params)
                st.success('Saved.')
                st.session_state['edit_result_dirty'] = True
            except Exception as e:
                st.error('Save error: ' + str(e))
                st.code(traceback.format_exc())
        if saveas_btn:
            name = new_name_input.strip() or (edited['case_name'] + '_copy')
            try:
                params = _build_params(edited, name)
                result = svc.calculate(params)
                svc.save(p=params, r=result)
                st.success('Saved as: ' + name)
            except Exception as e:
                st.error('Save As error: ' + str(e))
                st.code(traceback.format_exc())
        if del_btn:
            try:
                svc.delete_case(case_id)
                st.success('Deleted.')
                st.session_state['current_page']   = 'home'
                st.session_state['detail_case_id'] = None
                st.rerun()
            except Exception as e:
                st.error('Delete error: ' + str(e))
                st.code(traceback.format_exc())
        result = st.session_state.get('edit_result')
        if result:
            st.divider()
            st.subheader('Latest Result Preview')
            if st.session_state.get('edit_result_dirty'):
                st.warning('Parameters changed. Please recalculate.')
            m1, m2, m3, m4 = st.columns(4)
            m1.metric('BS Price',       '{:,.2f}'.format(result.bs_price))
            m2.metric('Binomial Price', '{:,.2f}'.format(result.binomial_price))
            m3.metric('MC Price',       '{:,.2f}'.format(result.mc_price))
            m4.metric('Weighted Price', '{:,.2f}'.format(result.weighted_price))
        else:
            st.info('Press Recalculate to see results.')
    with tab_result:
        result = st.session_state.get('edit_result')
        if result is None:
            st.info('Please run Recalculate in the Edit tab.')
        else:
            if st.session_state.get('edit_result_dirty'):
                st.warning('Parameters changed. Please recalculate.')
            st.subheader('Price Summary')
            m1, m2, m3, m4 = st.columns(4)
            m1.metric('BS Price',       '{:,.2f}'.format(result.bs_price))
            m2.metric('Binomial Price', '{:,.2f}'.format(result.binomial_price))
            m3.metric('MC Price',       '{:,.2f}'.format(result.mc_price))
            m4.metric('Weighted Price', '{:,.2f}'.format(result.weighted_price))
            st.divider()
            st.subheader('Greeks (BS)')
            g1, g2, g3, g4, g5 = st.columns(5)
            g1.metric('Delta', '{:.4f}'.format(result.delta))
            g2.metric('Gamma', '{:.6f}'.format(result.gamma))
            g3.metric('Theta', '{:.4f}'.format(result.theta))
            g4.metric('Vega',  '{:.4f}'.format(result.vega))
            g5.metric('Rho',   '{:.4f}'.format(result.rho))
            st.divider()
            with st.expander('Black-Scholes Detail', expanded=False):
                _show_scalars(result.bs_detail or {})
            with st.expander('Binomial Model Detail', expanded=False):
                d_bin = result.bin_detail or {}
                if d_bin:
                    _show_scalars(d_bin)
                    _show_list_items(d_bin)
                else:
                    st.info('No data.')
            with st.expander('Monte Carlo Detail', expanded=False):
                d_mc = result.mc_detail or {}
                if d_mc:
                    _show_scalars(d_mc, skip=('ST_hist', 'payoff_hist'))
                    payoffs = d_mc.get('payoff_hist', [])
                    if payoffs:
                        st.markdown('**Payoff Distribution**')
                        _plot_mc_histogram(payoffs, result.mc_price)
                else:
                    st.info('No data.')
    with tab_mc:
        st.subheader('Monte Carlo Simulation (Full Run)')
        if st.button('Run Simulation', type='primary'):
            with st.spinner('Calculating...'):
                try:
                    edited2 = _read_edit_state()
                    params  = _build_params(edited2)
                    res     = _get_service().calculate(params)
                    mc      = res.mc_detail or {}
                    payoffs = mc.get('payoff_hist', [])
                    if payoffs:
                        _plot_mc_histogram(payoffs, res.mc_price)
                    else:
                        st.warning('No payoff data available.')
                    r1c1, r1c2, r1c3 = st.columns(3)
                    r1c1.metric('MC Price',      '{:,.2f}'.format(res.mc_price))
                    r1c2.metric('95pct CI Low',  '{:,.2f}'.format(mc.get('ci95_lower', 0)))
                    r1c3.metric('95pct CI High', '{:,.2f}'.format(mc.get('ci95_upper', 0)))
                    r2c1, r2c2, r2c3 = st.columns(3)
                    r2c1.metric('ITM Ratio',     '{:.1%}'.format(mc.get('itm_ratio', 0)))
                    r2c2.metric('Std Error',     '{:.4f}'.format(mc.get('std_error', 0)))
                    r2c3.metric('N Simulations', '{:,}'.format(mc.get('n_simulations', 0)))
                except Exception as e:
                    st.error('MC Error: ' + str(e))
                    st.code(traceback.format_exc())
    st.divider()
    if st.button('Back to Home', key='btn_home_bottom'):
        st.session_state['current_page']   = 'home'
        st.session_state['detail_case_id'] = None
        st.rerun()


def render():
    show()
