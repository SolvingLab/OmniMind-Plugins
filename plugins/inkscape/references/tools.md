# Tools at 15fb592dd392f3b8bf1f99389113cf94704e13e4

Extracted from `@mcp.tool` decorators in `src/inkscape_mcp/tools/*.py`. Not from a registry search and not from PyPI `inkscape-mcp`.
Source: https://github.com/jjjsood/inkscape-mcp-server/tree/15fb592dd392f3b8bf1f99389113cf94704e13e4/src/inkscape_mcp/tools

`collection_set.py` has no `@mcp.tool`. It is not a tool.

## actions

File: `src/inkscape_mcp/tools/actions.py`

- `list_actions`
- `discover_extensions`
- `validate_action_chain`
- `run_action_chain`
- `run_raw_action`

## batch

File: `src/inkscape_mcp/tools/batch.py`

- `apply_edits`


## compose

File: `src/inkscape_mcp/tools/compose.py`

- `set_document_svg`
- `insert_svg_fragment`
- `compose_grid`
- `place_document`

## create

File: `src/inkscape_mcp/tools/create.py`

- `create_rect`
- `create_circle`
- `create_ellipse`
- `create_line`
- `create_polygon`
- `create_polyline`
- `create_path`
- `create_text`
- `add_linear_gradient`
- `add_radial_gradient`
- `create_group`
- `group_objects`
- `reparent_object`
- `create_use`

## discover

File: `src/inkscape_mcp/tools/discover.py`

- `how_do_i`

## document

File: `src/inkscape_mcp/tools/document.py`

- `open_document`
- `create_document`
- `reload_document`
- `inspect_document`

## dom

File: `src/inkscape_mcp/tools/dom.py`

- `delete_object`

## export

File: `src/inkscape_mcp/tools/export.py`

- `render_preview`
- `capture_frame`
- `list_frames`
- `export_document`
- `export_object`

## export_batch

File: `src/inkscape_mcp/tools/export_batch.py`

- `export_batch`
- `export_set`

## find

File: `src/inkscape_mcp/tools/find.py`

- `find_objects`

## live

File: `src/inkscape_mcp/tools/live.py`

- `check_live_support`
- `live_connect`
- `live_disconnect`
- `live_status`
- `live_install_helper`
- `live_arm_socket`
- `live_get_active_document`
- `live_get_selection`
- `live_inspect_selection`
- `live_render_view`
- `live_get_scene`
- `live_wait_for_change`
- `live_set_viewport`
- `live_sync_to_workspace`
- `live_apply_to_selection`
- `live_insert_svg`
- `live_set_selected_text`
- `live_export_selection`
- `live_diff_view`
- `live_session_step`

## optimize

File: `src/inkscape_mcp/tools/optimize.py`

- `svg_web_optimize`
- `optimize_set`

## paths

File: `src/inkscape_mcp/tools/paths.py`

- `simplify_path`
- `boolean_union`
- `boolean_difference`
- `combine_paths`
- `break_apart`
- `stroke_to_path`
- `cleanup_paths`

## profiles

File: `src/inkscape_mcp/tools/profiles.py`

- `export_web_profile`
- `create_icon_set`
- `export_print_profile`

## quality

File: `src/inkscape_mcp/tools/quality.py`

- `quality_report`
- `quality_report_set`

## save

File: `src/inkscape_mcp/tools/save.py`

- `save_document_as`

## snapshots

File: `src/inkscape_mcp/tools/snapshots.py`

- `create_snapshot`
- `list_snapshots`
- `restore_snapshot`
- `prune_snapshots`

## style

File: `src/inkscape_mcp/tools/style.py`

- `set_fill`
- `set_stroke`
- `set_opacity`
- `replace_color`
- `apply_palette`

## system

File: `src/inkscape_mcp/tools/system.py`

- `diagnose_runtime`
- `list_capabilities`
- `stat_artifact`
- `stat_artifacts`

## text_object

File: `src/inkscape_mcp/tools/text_object.py`

- `replace_text`
- `set_font`
- `duplicate_object`
- `rename_object`

## transform

File: `src/inkscape_mcp/tools/transform.py`

- `move_object`
- `scale_object`
- `rotate_object`
- `resize_canvas`
- `normalize_viewbox`
- `fit_to_content`
- `tile`

## transform_objects

File: `src/inkscape_mcp/tools/transform_objects.py`

- `transform_objects`

## validate

File: `src/inkscape_mcp/tools/validate.py`

- `validate_document`

Tool count: 99

## Resources

### document

- `inkscape://document/{doc_id}/summary`
- `inkscape://document/{doc_id}/tree`
- `inkscape://document/{doc_id}/layers`
- `inkscape://document/{doc_id}/objects`
- `inkscape://document/{doc_id}/styles`
- `inkscape://document/{doc_id}/fonts`
- `inkscape://document/{doc_id}/assets`
- `inkscape://documents`

### live

- `inkscape://live/session`
- `inkscape://live/selection`
- `inkscape://live/view`
- `inkscape://live/events`
- `inkscape://live/operations`

### prompts

- `inkscape://prompts`

### runtime

- `inkscape://runtime/capabilities`
- `inkscape://runtime/intents`

## Prompts

### authoring

- `compose_artwork`
- `restyle_artwork`

### library

- `prepare_web_export`
- `prepare_icon_set`
- `prepare_print_export`
- `theme_recoloring`

### live

- `live_canvas_assist`

