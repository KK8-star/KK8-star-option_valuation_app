import pathlib

content = pathlib.Path('app.py').read_text(encoding='utf-8')

# 修正前（問題のあるコード）
old = '''    if sel != st.session_state["current_page"]:
        st.session_state["current_page"] = sel
        st.session_state.pop("detail_case_id", None)
        st.session_state.pop("selected_case_id", None)
        st.rerun()'''

# 修正後（radioの値ではなくsession_stateを優先）
new = '''    # サイドバー操作による遷移のみ処理
    # (ボタン等による遷移はst.rerun済みのためここでは無視)
    if sel != st.session_state["current_page"]:
        # radioのkeyをリセットして再描画された場合は無視
        # selがページキーと一致し、かつradioが実際に操作された場合のみ遷移
        st.session_state["current_page"] = sel
        st.session_state.pop("detail_case_id", None)
        st.session_state.pop("selected_case_id", None)
        st.rerun()'''

# 根本的な修正: radioのindexをcurrent_pageから毎回計算することで
# session_stateが変わってもradioが追いつくようにする
# → すでにradio_indexで対応済みだが、radioのkey固定が問題
# 真の修正: radioにkeyを使わず、session_stateで制御する

new_sidebar = '''    try:
        radio_index = PAGE_KEYS.index(st.session_state["current_page"])
    except ValueError:
        radio_index = 0

    sel = st.radio(
        "メニュー",
        PAGE_KEYS,
        index=radio_index,
        key=f"nav_radio_{st.session_state['current_page']}",
        label_visibility="collapsed",
    )

    if sel != st.session_state["current_page"]:
        st.session_state["current_page"] = sel
        st.session_state.pop("detail_case_id", None)
        st.session_state.pop("selected_case_id", None)
        st.rerun()'''

old_sidebar = '''    try:
        radio_index = PAGE_KEYS.index(st.session_state["current_page"])
    except ValueError:
        radio_index = 0

    sel = st.radio(
        "メニュー",
        PAGE_KEYS,
        index=radio_index,
        key="nav_radio",
        label_visibility="collapsed",
    )

    if sel != st.session_state["current_page"]:
        st.session_state["current_page"] = sel
        st.session_state.pop("detail_case_id", None)
        st.session_state.pop("selected_case_id", None)
        st.rerun()'''

if old_sidebar in content:
    content = content.replace(old_sidebar, new_sidebar)
    pathlib.Path('app.py').write_text(content, encoding='utf-8')
    print('修正成功: radioのkeyを動的に変更するよう修正しました')
else:
    print('修正対象が見つかりません。手動確認が必要です')
    # 現在のradio部分を表示
    for i, line in enumerate(content.split('\n'), 1):
        if 'nav_radio' in line or 'radio_index' in line or 'sel' in line:
            print(f'{i:3}: {line}')
