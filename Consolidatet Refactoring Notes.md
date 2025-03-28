## Consolidated Refactoring Notes & Action Items

This list summarizes observations made during the refactoring of the System Prompt List feature.

**A. Refactoring Completed / Confirmed:**

*   **Core Data Model:** Switched from `MenuSystemPrompt` (using `name`, `prompt_text`, `priority`) to `SystemPrompt` (using `id`, `title`, `content`, `pinned`, `pin_order`, `list_order`). (P1S1, P2S2f)
*   **Persistence:** Primary persistence confirmed and refactored to use JSON (`system_prompts_U.json`), storing the new `SystemPrompt` model. (P1S2a, P1S2b)
*   **ID-Based Logic:** All operations (add, delete, edit, pin, move, activate) now consistently use `prompt.id` instead of `display_idx`. (P1S2e, P1S2f, P2S2e)
*   **Order Management:** Replaced `display_order_U` list with logic based on `pin_order` (for pinned items) and `list_order` (for numbered items). (P1S2a, P1S2e, P1S2f)
*   **Loading/Saving:** Refactored `load_prompts` (incl. migration logic for old JSON format) and `save_prompts`. (P1S2a, P1S2b)
*   **Default Prompts:** Updated `_create_default_prompts` for the new model and ordering. (P1S2b)
*   **UI Entry Point:** Updated main menu to call the new `_manage_system_prompts` function. (P2S2a)
*   **UI Display (`rich`):** Implemented new display logic using `rich.Panel` for pinned items (with DFG keys) and a numbered list for others. (P2S2c)
*   **UI Interaction (`inquirer`):** Implemented `inquirer.List` for selection, handling prompt selection, "Add New", and "Back". (P2S2d)
*   **Dynamic Action Menu:** `_show_prompt_actions_menu` now dynamically builds context-sensitive actions. (P2S2e)
*   **New/Refactored Actions:** Implemented `Activate and Chat`, `Move to Top/Bottom/Position`, `Edit Title/Content` logic in `config.py` and UI. (P1S2f, P2S2e)
*   **Status Markers:** Updated `_get_status_markers` to use `prompt.pinned`. (P2S2a)
*   **Error Handling:** Added more comprehensive `try/except` blocks, specific validation error catching, and `KeyboardInterrupt` handling. (P1S2e, P2S2d, P2S2e, P2S2f)
*   **UX Improvements:** Added success messages, confirmation prompts (delete), default values in edits, `inquirer.Editor` usage, carousel navigation. (P2S2e, P2S2f)
*   **Code Structure:** Removed old methods (`_display_prompts_list`, old action methods) and simplified navigation structure. (P1S2f, P2S2a)

**B. Immediate Verification / Potential Bugs (Post-Testing):**

1.  **Filename Consistency:** Verify `save_prompts` and `load_prompts` consistently use `"system_prompts_U.json"`. (P1S2b)
2.  **Lingering `display_idx` / `prompts.keys()` Usage:** Double-check the codebase (especially parts *outside* `config.py` and `menu_helpers.py` that might interact with prompts) for any remaining reliance on list index or fragile dictionary key ordering. Replace with ID-based logic or sorting by order attributes. (P1S2a, P1S2c, P1S2d)
3.  **Return Values:** Ensure any methods previously returning `"system_prompts"` now return appropriate signals (e.g., `None` to stay, specific string for mode change) compatible with `handle_navigation`. (P2S2a)
4.  **Keyboard Shortcuts/Navigation:** Thoroughly test `inquirer` list navigation with arrow keys, DFG prefix jumps, and number prefix jumps. Test `carousel=True` behavior. (P2S2d)

**C. Validation & Robustness Checks:**

1.  **Empty List Handling:** Confirm behavior when deleting the *last* prompt (active prompt selection, display). (P1S2c)
2.  **`toggle_pin_status` Validation:** Ensure `new_list_order_on_unpin` is validated against bounds (`0 <= new_order <= count`). (P1S2e)
3.  **`move_prompt_list_order` Bounds Check:** Consider adding check if `target_order` is valid before searching for `target_prompt`. (P1S2f)
4.  **`edit_content` Validation:** Current validation is minimal; consider if stricter checks (e.g., non-empty?) are needed. (P1S2f)
5.  **UUID Generation:** Add `try/except` around UUID generation if it's considered potentially fallible in your environment (usually very reliable). (P1S2b)
6.  **Sorting Robustness:** Ensure sorting keys (`pin_order`, `list_order`) reliably handle expected values; add default/fallback values only if `None` is genuinely possible where it shouldn't be (should be enforced by `config.py` logic). (P2S2b)
7.  **Attribute Access:** While Pydantic helps, consider `try/except AttributeError` around `prompt.title` etc. in the UI if there's *any* doubt about data integrity. (P2S2c)

**D. UX Enhancements (Consider Implementing):**

1.  **Visual Spacing:** Add spacing (`console.print()`) between panels/sections in the list display for better readability. (P2S2c)
2.  **Help Text/Footer:** Add a footer (e.g., `rich.Panel` or simple text) below the `inquirer` list explaining navigation (Arrows, DFG, Numbers, Enter). (P2S2c, P2S2d)
3.  **`inquirer` List Separation:** Consider adding separator lines (`inquirer.Separator()`) in the `choices` list between pinned, numbered, and action items for clearer visual grouping. (P2S2d)
4.  **Test `inquirer` Markers:** Verify how `●`/`○`/`📌` markers look within the `inquirer` selection highlight; adjust formatting if needed. (P2S2d)

**E. Code Quality / Consistency:**

1.  **Helper Methods:** Consider extracting common logic (e.g., getting sorted lists, finding next available order) into helper methods within `config.py` or `menu_helpers.py`. (P1S2d)
2.  **Documentation:** Document conventions like `list_order=-1` for pinned items (if used) and the consistent action pattern (Validate -> Change -> Save). (P1S2e, P1S2f)

**F. Future Feature Ideas:**

*   **Content Editing:** Use `inquirer.Editor` consistently (if not already done everywhere). (P2S2e)
*   **Preview:** Add a "Preview Content" action. (P2S2e, P2S2f)
*   **Duplicate:** Add a "Duplicate Prompt" action. (P2S2e)
*   **Test Prompt:** Add action to run a quick test chat with the selected prompt temporarily active. (P2S2e)
*   **Templates:** Add ability to create new prompts from predefined templates. (P2S2f)
*   **Content Validation:** Add validation based on potential API limits. (P2S2f)
*   **Help Text (Content):** Add guidance within the "Add/Edit Content" flow. (P2S2f)

**G. Lingering Dependencies / Cleanup:**

1.  **`BaseSystemPrompt`:** Address the `name` field if it's still present and causing issues elsewhere. (P1S1)
2.  **SQLAlchemy Models:** Decide if `MenuSystemPromptModel` and related SQLAlchemy code should be updated to match the new structure (if DB persistence is desired *later*) or removed entirely if JSON is the definitive long-term solution. (P1S1, P1S2a)

---
