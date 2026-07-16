# Mercury 浠诲姟鍒嗛厤琛?
> 鏇存柊锛?026-07-16 | 浠撳簱锛歚docs/TASK_ASSIGNMENT.md`

---

## 鍥㈤槦

| 鎴愬憳 | 瑙掕壊 | 璐熻矗 |
|------|------|------|
| **A** | 鍚庣 | 鏁版嵁搴撱€丼tore銆丷eader绠＄嚎銆佹爣绛炬牳蹇冦€丏igest瀵煎嚭 |
| **B** | AI+绠＄悊 | Agent杩愯鏃躲€丩LM Provider銆佹憳瑕?缈昏瘧/鏍囩Agent銆佹彁绀鸿瘝妯℃澘 |
| **C** | UI | Qt鐣岄潰銆佷富棰樸€佸璇濇銆乮18n |

---

## 鏁翠綋杩涘害

```
Phase 0 [鈻堚枅鈻堚枅] 鏂囨。 鉁?Phase 1 [鈻堚枅鈻堚枅] 鍩虹鎼缓 鉁?Phase 2 [鈻堚枅鈻堚枒] Reader 馃攧 G2.1鉁?G2.2鉁咃紝UI瀵规帴瀹屾垚锛屽緟楠屾敹
Phase 3 [鈻堚枅鈻堚枅] Agent  鉁?B鍏ㄩ儴瀹屾垚锛? Agent + Runtime + Provider + Templates锛?Phase 4 [鈻堚枅鈻堚枅] 鏍囩 鉁?G4.1浜や粯锛坣ormalizer + tag_store + cooccurrence锛?Phase 5 [鈻戔枒鈻戔枒] 绗旇/瀵煎嚭/缁熻/i18n
Phase 6 [鈻戔枒鈻戔枒] CI/鎵撳寘
```

---

## 鎺ュ彛绉讳氦鐘舵€?
| 闂ㄦ帶 | 璋佲啋璋?| 鍐呭 | 鐘舵€?|
|------|-------|------|------|
| G2.1 | A鈫払,C | `RenderedContent` + `ReaderPipeline.build()` | 鉁?宸插喕缁?|
| G2.2 | A鈫扖 | `EntryStore` 鏂囩珷绠＄悊鏂规硶锛?涓柟娉曞叏閮ㄥ埌浣嶏級 | 鉁?宸蹭氦浠?|
| G3.1 | B鈫扐 | `AgentRuntime` 鍗曚緥娉ㄥ叆 | 鉁?宸插喕缁?|
| G3.2 | B鈫扖 | `AgentUIEvent` + Signals | 鉁?宸插喕缁?|
| G3.3 | B鈫扖 | `ProviderConfig` + `LLMRouter` | 鉁?宸插喕缁?|
| G4.1 | A鈫払,C | `normalize()` + `TagStore` | 鉁?宸蹭氦浠?|

---

## A 闇€瑕佸仛鐨?
| # | 浠诲姟 | 璇存槑 | 闃诲璋?|
|---|------|------|--------|
| 1 | `store/entry_store.py` 鍔?涓柟娉?| 鉁?mark_read, mark_unread, batch_mark_read, toggle_star, search, soft_delete 鍏ㄩ儴瀹屾垚 | 鈥?|
| 2 | `core/tags/normalizer.py` | 鉁?TagNormalizer锛圲nicode NFC + 鏅鸿兘灏忓啓 + 鍒悕瑙ｆ瀽锛?| 鈥?|
| 3 | `store/tag_store.py` | 鉁?TagStore锛圕RUD + 鏂囩珷鍏宠仈 + 鎵归噺鎵撴爣 + 鍒悕绠＄悊 + 涓存椂鏍囩锛夆啋 **G4.1** | 鈥?|
| 4 | `core/tags/cooccurrence.py` | 鉁?CooccurrenceEngine锛圝accard 鍏辩幇鎺ㄨ崘 + 5min 缂撳瓨锛?| 鈥?|
| 5 | `store/note_store.py` | 绗旇CRUD | C鐨勭瑪璁扮紪杈戝櫒 |
| 6 | `core/digest/exporter.py` + 妯℃澘 | Jinja2瀵煎嚭(Hugo鍏煎) | C鐨勫鍑哄璇濇 |
| 7 | `.github/workflows/ci.yml` | 涓夊钩鍙癈I | 鈥?|
| 8 | PyInstaller鎵撳寘 | Windows .exe + macOS .app | 鈥?|

---

## B 闇€瑕佸仛鐨?
| # | 浠诲姟 | 璇存槑 | 渚濊禆 |
|---|------|------|------|
| 1 | `core/agent/summary.py` | 鉁?SummaryAgent锛堟墜鍔?鑷姩锛岄槻鎶栵紝缂撳瓨锛夊凡瀹屾垚 | G2.1鉁?G3.1鉁?|
| 2 | `core/agent/translation.py` | 鉁?TranslationAgent锛堝垎娈碉紝骞跺彂锛屽弻璇璈TML锛夊凡瀹屾垚 | G2.1鉁?G3.1鉁?|
| 3 | G3.3鍐荤粨 | 鉁?`ProviderConfig` + `LLMRouter` 鎺ュ彛宸茬‘璁ゅ喕缁?| 鈥?|
| 4 | `core/agent/tagging.py` | 鉁?TagAgent锛圠LM寤鸿+JSON瑙ｆ瀽瀹归敊+瑙勮寖鍖?鍘婚噸+鍙€変緷璧栨敞鍏ワ級宸插畬鎴?| G4.1猬?|

---

## C 闇€瑕佸仛鐨?
| # | 浠诲姟 | 璇存槑 | 渚濊禆 |
|---|------|------|------|
| 1 | `ui/reader/theme.py` + `theme_manager.py` | 鉁?涓婚绯荤粺宸插畬鎴愶紙鍚?LIGHT/DARK 鍙岃皟鑹叉澘 + 棰勮锛?| 鈥?|
| 2 | `ui/reader/reader_view.py` 绠＄嚎瀵规帴 | 鉁?宸插鎺?ReaderPipeline + WebEngine 闄嶇骇 | G2.1鉁?|
| 3 | `ui/entry_list.py` 鎵╁睍 | 鉁?宸茶/鏀惰棌/鍙抽敭鑿滃崟/鎼滅储鏍?宸插畬鎴?| G2.2鉁?|
| 4 | 鎼滅储鏍忕粍浠?| 鉁?宸查泦鎴愬湪 entry_list.py | G2.2鉁?|
| 5 | `ui/reader/reader_toolbar.py` | 鉁?妯″紡鍒囨崲+瀛楀彿+涓婚+鍐呭瀹藉害 宸插畬鎴?| G2.1鉁?|
| 6 | `ui/dialogs/opml_dialog.py` | OPML瀵煎叆瀵煎嚭UI | Phase1鉁?|
| 7 | `ui/settings/provider_panel.py` | LLM鎻愪緵鑰呴厤缃?| G3.3猬?|
| 8 | `ui/settings/agent_panel.py` | Agent绫诲瀷璁剧疆 | G3.3猬?|
| 9 | `ui/reader/summary_panel.py` | 鎽樿闈㈡澘(鍙姌鍙?娴佸紡) | G3.2鉁?|
| 10 | 缈昏瘧鎸夐挳+鍙岃娓叉煋 | reader_toolbar+reader_view鎵╁睍 | G3.2鉁?|
| 11 | `ui/dialogs/tag_manager_dialog.py` | 鏍囩绠＄悊 | G4.1猬?|
| 12 | 鏍囩寰界珷+绛涢€夋爮 | reader_view+sidebar鎵╁睍 | G4.1猬?|
| 13 | `ui/reader/note_editor.py` | 绗旇缂栬緫鍣?5s闃叉姈) | 鈥?|
| 14 | `ui/dialogs/export_dialog.py` | 瀵煎嚭瀵硅瘽妗?妯℃澘棰勮) | 鈥?|
| 15 | `ui/settings/usage_panel.py` | 鐢ㄩ噺缁熻闈㈡澘 | 鈥?|
| 16 | i18n | 涓嫳鏂?ts鐢熸垚+杩愯鏃跺垏鎹?| 鎵€鏈塙I绋冲畾鍚?|
| 17 | 楂楧PI/璺ㄥ钩鍙伴獙璇?| 125%/150%/200%缂╂斁 | Phase 6 |

---

## 褰撳墠闃诲鐐?
```
锛堟棤锛夆€?Phase 0鈥? 鍏ㄩ儴浜や粯锛孭hase 5 寰呭惎鍔?```

---

## 鏈鏇存柊鎽樿锛?026-07-16锛?
| 鍙樻洿 | 璇︽儏 |
|------|------|
| 鉁?A-1 瀹屾垚 | `EntryStore` 6涓柟娉曞叏閮ㄥ疄鐜帮紙mark_read/unread, batch_mark_read, toggle_star, search, soft_delete锛?|
| 鉁?G2.2 浜や粯 | A鈫扖 鏂囩珷绠＄悊鎺ュ彛宸插氨缁?|
| 鉁?B-1 瀹屾垚 | `SummaryAgent` 瀹炵幇瀹屾瘯锛堢紦瀛樸€佹祦寮忋€丄gentStore鎸佷箙鍖栵級 |
| 鉁?B-2 瀹屾垚 | `TranslationAgent` 瀹炵幇瀹屾瘯锛堝垎娈点€佸苟鍙戙€佸弻璇璈TML缁勮锛?|
| 鉁?B-3 瀹屾垚 | G3.3 姝ｅ紡鍐荤粨 鈥?`ProviderConfig` + `LLMRouter` 鎺ュ彛纭绋冲畾 |
| 鉁?B-4 瀹屾垚 | `TagAgent` 瀹炵幇瀹屾瘯锛圠LM寤鸿銆丣SON瀹归敊瑙ｆ瀽銆佽鑼冨寲鍘婚噸銆佸彲閫変緷璧栨敞鍏ワ級 |
| 鉁?C-1~5 瀹屾垚 | 涓婚绯荤粺銆乺eader_view绠＄嚎瀵规帴銆乪ntry_list鎵╁睍銆佹悳绱㈡爮銆乺eader_toolbar |
| 鉁?styles.py | `application_stylesheet()` 鏀逛负 palette 椹卞姩锛屾敮鎸佷寒/鏆楀弻涓婚 |

---

## G2.1 鎺ュ彛閫熸煡锛圓鈫払,C, 宸插喕缁擄級

```python
# core/reader/pipeline.py
@dataclass
class RenderedContent:
    html: str        # 娓叉煋HTML
    title: str
    byline: str
    markdown: str    # Agent娑堣垂
    from_cache: bool

class ReaderPipeline:
    async def build(entry_id: int) -> RenderedContent: ...
```

## G3.1+G3.2 鎺ュ彛閫熸煡锛圔鈫扐,C, 宸插喕缁擄級

```python
# core/agent/runtime.py
@dataclass(frozen=True)
class AgentUIEvent:
    run_id: str; entry_id: int; agent_type: str
    status: str      # queued|running|done|error|cancelled
    chunk: str = ""; progress: float = 0.0
    error: str | None = None; result_json: str | None = None

class AgentRuntime:
    def register(agent_type, handler) -> None: ...
    def submit(entry_id, agent_type) -> str: ...  # returns run_id
    def cancel(run_id) -> None: ...
    def broadcast_chunk(run_id, entry_id, agent_type, text) -> None: ...
    signals: AgentSignals  # state_changed + chunk_received (PySide6 Signals)
```
