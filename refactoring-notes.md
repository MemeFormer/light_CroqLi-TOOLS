# Refactoring Notes

This document tracks additional observations and potential improvements noticed during the step-by-step refactoring process. These items will be addressed after completing all planned phases and steps.

## Format
Each entry should include:
- Phase/Step where it was noticed
- Description of the observation/issue
- Potential impact
- Suggested solution (if applicable)

## Phase 1, Step 1 Observations
1. BaseSystemPrompt still uses `name` instead of `title` - this might need to be addressed in a future step
2. SQLAlchemy models (MenuSystemPromptModel) still reference old structure - might need updating later
3. Any code using MenuSystemPrompt will need to be updated to use SystemPrompt

## Phase 1, Step 2a Observations
1. Some methods still need to be updated to handle the new data structure (e.g., `_reorder_after_pin_change`, `move_prompt`)
2. The `prompts.keys()[index]` pattern might be problematic since dictionary keys don't maintain order - we might need to sort by `list_order`
3. The `save_prompts` method needs to be implemented in the next step
4. We might need to update the SQLAlchemy models to match the new structure
5. The `_create_default_prompts` method might need adjustment for proper list_order and pin_order handling

## Phase 1, Step 2b Observations
1. The save_prompts filename is still "system_prompts.json" - might need to be updated to "system_prompts_U.json" as specified in the instructions
2. We might want to add error handling for UUID generation in _create_default_prompts
3. The first_prompt selection in _create_default_prompts assumes the dictionary is ordered - might need to be more explicit about order

## Phase 1, Step 2c Observations
1. We might want to add validation for the case where all prompts are deleted
2. The prompts.keys()[display_idx] pattern is still used in several methods - this might need to be addressed in a future step
3. The pin_prompt and move_prompt methods still use display_idx - these might need to be updated in future steps

## Phase 1, Step 2d Observations
1. Other methods still use display_idx - they will need to be updated in future steps
2. The sorting logic for finding new active prompt might be useful in other places - could be extracted to a helper method
3. We might want to add a method to get prompts in sorted order since we're using that pattern

## Phase 1, Step 2e Observations
1. The old implementation used display indices and dictionary manipulation, while the new one uses direct prompt ID references and attribute updates
2. The new implementation has better error handling and validation
3. The list_order=-1 for pinned prompts might need to be documented as a special value
4. We might want to add validation for new_list_order_on_unpin to ensure it's not greater than the current maximum list_order

## Phase 1, Step 2f Observations
1. The changes were split across two sessions due to timeout, but we successfully:
   - Removed the old update_prompt method that used display_idx
   - Implemented all new move and edit methods as specified
2. The move_prompt_list_order method could potentially benefit from a bounds check on the target_order before attempting to find a target prompt
3. The edit_content method's validation is minimal (just checking for None) - we might want to consider additional validation in the future if needed
4. All the new methods consistently follow the pattern of:
   - Validating prompt_id exists
   - Performing specific validation
   - Making changes
   - Saving
   This consistent pattern could be documented as a best practice for future method additions

## Phase 2, Step 2a Observations
1. The _manage_system_prompts method doesn't exist yet - it will need to be implemented in the next step
2. We removed the old prompts submenu structure, which will simplify navigation and maintenance
3. The status markers now correctly use the new pinned attribute, making it consistent with our data model changes
4. Some methods still reference "system_prompts" as a return value (e.g., _display_prompts_list) - these will need to be updated in future steps
5. There are still some old methods (_display_prompts_list, _show_prompt_actions_menu) that use the old display_idx approach - these will need to be refactored in upcoming steps

## Phase 2, Step 2b Observations
1. The method signature includes Optional[str] return type to maintain consistency with other menu methods that return navigation signals
2. Added a safety check for None pin_order in the pinned prompts sorting (using float('inf') as fallback)
3. The method currently uses load_prompts() instead of the old load_systemprompts_U() - we should verify this is the correct new method name
4. The while True loop is in place but currently returns immediately - this will be expanded in future steps
5. We might want to consider refreshing all_prompts inside the while loop since it might change during user interactions
6. The sorting logic assumes pin_order and list_order are always set appropriately - we might want to add defensive programming in future steps

## Phase 2, Step 2c Observations
1. Added a safety check `if i < len(pinned_keys)` to prevent index errors if there are more pinned prompts than available hotkeys
2. Using `title` attribute for display - we should verify this is the correct attribute name (vs. name or something else)
3. The display now clearly separates pinned and numbered prompts with visual hierarchy
4. We might want to add some spacing between the panels and sections for better readability
5. Consider adding a footer or help text showing available actions (could be another Panel)
6. The prompt.title access might need error handling in case the attribute is missing or None

## Phase 2, Step 2d Observations
1. Added error handling for both KeyboardInterrupt and general prompt interruption (when answers is None)
2. The _show_prompt_actions_menu method needs to be updated to accept a prompt object instead of an index
3. The _add_new_prompt method might need updates to work with the new data model
4. We're using prompt.id for selection tracking - need to ensure this exists in the data model
5. The display strings include status markers which might affect selection display in inquirer - might need testing
6. Consider adding visual separation between pinned prompts, numbered prompts, and special actions in the inquirer list
7. The carousel=True option allows for easier navigation but might need testing with keyboard shortcuts
8. We might want to add a help text or legend showing available keyboard shortcuts

## Phase 2, Step 2e Observations
1. Action Menu Improvements:
   - Actions are now context-sensitive based on prompt state (active/pinned)
   - Added new actions like "Activate and Chat" for better UX
   - Added more movement options (top/bottom/position)
   - Added edit capabilities for both title and content

2. UX Enhancements:
   - Added success messages after actions
   - Added warning when deleting active prompt
   - Added validation for numeric inputs
   - Used default values in edit prompts
   - Added carousel navigation for better keyboard control

3. Data Model Considerations:
   - Using prompt.id consistently for all operations
   - Assuming prompt.title exists (previously used name)
   - Assuming prompt.content exists for editing

4. Error Handling:
   - Added comprehensive error handling with try/except blocks
   - Added KeyboardInterrupt handling for better UX
   - Added validation for position inputs

5. Future Improvements to Consider:
   - Could use inquirer.Editor for content editing (multiline support)
   - Might want to add a preview feature for content
   - Could add a "duplicate prompt" feature
   - Could add a "test prompt" feature that shows how it would be used

## Phase 2, Step 2f Observations
1. UX Improvements:
   - Using inquirer.Editor provides a better multiline editing experience for content
   - Added feedback for cancelled prompt creation
   - Consistent error message formatting with other methods

2. Error Handling:
   - More granular error handling helps users understand what went wrong
   - Separate handling for validation errors vs unexpected errors
   - Graceful handling of cancellation

3. Integration Points:
   - Method now properly integrates with _manage_system_prompts loop
   - Removed old MenuSystemPrompt model dependency
   - Uses new config.add_prompt interface correctly

4. Potential Future Improvements:
   - Could add a preview of the prompt before confirming
   - Could add template selection for common prompt types
   - Could add validation for maximum content length if there are API limits
   - Could add help text explaining prompt content format/best practices

5. Migration Considerations:
   - Old code used 'name' while new code uses 'title' - ensure data migration handles this
   - Removed 'priority' field as pinning is now handled separately

## Observations 



###########################

