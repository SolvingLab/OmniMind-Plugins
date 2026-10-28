# Tools excerpt at 3e10efb9963be36ee1209f8f9ebd2cc6efcfcc46

Not a fabricated full list. README says standalone exposes about 242 tools and bridge about 245. `docs/en/tools-reference.md` was not fetched. Names below are copied from that commit's README tool table.

`server.py` registers modules including geometry, curves, solids, surfaces, mesh, transform, composition, annotation, layers, materials, io, analysis, query, document_config, geometry_validation, drawing, schedule, blocks, environment, bim_io, ff_skin, ff_paneling, ff_curvature, ff_fields, rhinoscript_docs, bridge_admin, templates for both modes. Bridge-only modules include render, scripting, history, batch, batch_call, deformation, nurbs, subd, surface_match, extraction, control_points, paneling, display, components, parameters, canvas, data_tree.

Notable names from the README table:

- `rhino_point`, `rhino_circle`, `rhino_helix`, `rhino_nurbs_curve`, `rhino_rebuild_curve`
- `rhino_curve_length`, `rhino_curve_point_at`, `rhino_curve_split`
- `rhino_box`, `rhino_sphere`, `rhino_boolean_union` (bridge)
- `rhino_loft`, `rhino_sweep1`, `rhino_revolve` (bridge)
- `rhino_mesh_box`, `rhino_weld_mesh` (bridge)
- `rhino_array_polar`, `rhino_orient`, `rhino_flow` (bridge)
- `rhino_text_dot`, `rhino_dimension_linear` (bridge)
- `rhino_layer_create`, `rhino_block_insert` (bridge)
- `rhino_material_create`, `rhino_render_viewport` (bridge)
- `rhino_save`, `rhino_export_step` (bridge)
- `rhino_volume`, `rhino_zebra` (bridge)
- `rhino_list_objects`, `rhino_document_summary`, `rhino_get_selected_objects` (bridge)
- `rhino_zoom_extent`, `rhino_named_view_save` (bridge)
- `rhino_execute_python`, `rhino_execute_csharp` (bridge)
- `rhino_search_rhinoscript_functions`, `rhino_get_rhinoscript_docs`
- `rhino_undo`, `rhino_redo` (bridge)
- `rhino_batch_modify` (bridge)
- `rhino_bend`, `rhino_twist`, `rhino_taper`, `rhino_flow_along_curve` (bridge)
- `gh_set_slider`, `gh_bake_to_rhino`, `gh_data_tree_get` (bridge)
- `rhino_drawing_sheet_create`, `rhino_drawing_title_block_add`, `rhino_drawing_view_place` (bridge)
- `rhino_schedule_by_layer`, `rhino_schedule_by_user_text`, `rhino_object_quantity`
- `rhino_block_define`, `rhino_block_insert`, `rhino_block_explode` (bridge)
- `rhino_sun_position`, `rhino_sun_path`, `rhino_shadow_project`
- `rhino_skin_from_sections`, `rhino_panel_curvature_classify`, `rhino_attractor_displace_points`
- `rhino_bim_metadata_set`, `rhino_export_ifc` (bridge), `rhino_import_ifc` (bridge), `rhino_export_gbxml` (bridge)
- `rhino_material_preset_list`, `rhino_material_preset_create`, `rhino_environment_set` (bridge)
- `rhino_camera_set`, `rhino_light_add`, `rhino_render_setup`, `rhino_render_to_file`, `rhino_turntable_render` (bridge)
- `rhino_direct_irradiance`, `rhino_daylight_factor`

Prompts named in the README: `general_strategy`, `rhinoscript_workflow`, `viewport_workflow`, `parametric_workflow`, `bim_authoring_workflow`, `design_dialogue_workflow`, `freeform_workflow`.

Do not call a name that is not in this excerpt unless the operator has opened the unfetched tools-reference. Bridge-marked names stay unavailable until `force_mode=bridge` and a real Rhino 8 session exists. This package does not create that session.
