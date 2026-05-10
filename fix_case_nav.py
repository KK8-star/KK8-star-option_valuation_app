import re

path = "src/ui/pages/case_list.py"
content = open(path, encoding="utf-8").read()

old = '''                if st.button("詳細", key=btn_key_detail, use_container_width=True):
                    st.session_state["selected_case_id"] = case["id"]
                    st.session_state["current_page"] = "投 譁ｰ隕剰ｩ穂ｾ｡"
                    st.rerun()'''

new = '''                if st.button("詳細", key=btn_key_detail, use_container_width=True):
                    st.session_state["selected_case_id"] = case["id"]
                    st.session_state["current_page"] = "評価詳細"
                    st.rerun()'''

if old in content:
    content = content.replace(old, new)
    open(path, "w", encoding="utf-8").write(content)
    print("case_list.py 修正完了")
else:
    print("対象文字列が見つかりません - 手動確認が必要")
    # 該当行を探して表示
    for i, line in enumerate(content.split("\n")):
        if "selected_case_id" in line or "current_page" in line:
            print(f"  {i+1}: {line}")
