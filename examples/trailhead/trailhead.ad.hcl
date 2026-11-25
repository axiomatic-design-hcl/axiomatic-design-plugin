# Trailhead: an offline day-hiking companion with an uncoupled design.
# Every sibling matrix and the leaf-level master matrix are diagonal.
#
# Run: adhcl validate examples/trailhead/trailhead.ad.hcl
# The source profile passes. The architecture profile reports two
# unresolved_refinement errors: the parent diagonals DP2->FR2 and DP3->FR3 sit
# above leaf level, and core version 1 has no review input for the outcome
# argument that would discharge them. They are kept because they are true.
#
# Folder names in the pv addresses follow the adhcl-scaffold layout contract:
# src/dp<N>_<dp label>/pv<N>_<pv label>, tests/fr<N>_<fr label>.

design "trailhead" {
  boundary = "A mobile app that runs on the hiker's device and has no app backend. It includes the offline map, the track recorder, the SOS sender, and the forecast view. The map tile publisher, the weather service, the SMS carrier, the GPS hardware, and the operating system are outside the boundary. SMS delivery by the carrier is outside the boundary; the app is responsible up to the handoff to the operating system."
  level    = "architecture"
  workload = workload.day_hike
  origin   = "proposed"
}

# ── Stakeholders and needs ───────────────────────────────────

stakeholder "day_hiker" {
  role = "A hiker on a trip of one day or less, often without mobile data."
}

stakeholder "emergency_contact_person" {
  role = "The person whom the hiker names to receive an SOS."
}

need "navigate_offline" {
  statement   = "See the trail map where there is no mobile data."
  why         = "Most trails have little or no mobile coverage."
  stakeholder = stakeholder.day_hiker
  origin      = "proposed"
}

need "keep_a_record" {
  statement   = "Keep a record of the route that was actually walked."
  why         = "Hikers review, share, and repeat their routes."
  stakeholder = stakeholder.day_hiker
  origin      = "proposed"
}

need "get_help" {
  statement   = "Tell a chosen person where the hiker is when the hiker needs help."
  why         = "A rescue starts sooner when the rescuers know the position."
  stakeholder = stakeholder.emergency_contact_person
  origin      = "proposed"
}

need "plan_for_weather" {
  statement   = "Know the forecast for the trail before and during the hike."
  stakeholder = stakeholder.day_hiker
  origin      = "proposed"
}

# ── Constraints, assumptions, workload ───────────────────────

constraint "offline_first" {
  statement = "The map, the track recorder, and the SOS sender work without mobile data."
  kind      = "operating"
  origin    = "proposed"
}

constraint "on_device_only" {
  statement = "All state stays on the hiker's device. The app has no backend of its own."
  kind      = "architecture"
  origin    = "proposed"
}

constraint "sampling_range" {
  statement = "The hiker can set the track sampling interval from 1 s to 10 s."
  kind      = "configuration"
  origin    = "proposed"
}

assumption "location_service_shared" {
  statement = "The operating system location service serves several clients at once. A request from one client does not cancel, pause, or delay the updates of another client."
  status    = "to_validate"
  origin    = "proposed"
}

assumption "preallocation_honored" {
  statement = "The operating system keeps preallocated file space reserved, so other writes cannot take the space that the fix log reserved."
  status    = "to_validate"
  origin    = "proposed"
}

workload "day_hike" {
  description = "One hiker with one device. A trip lasts up to 12 hours. A region pack is up to 500 MB. The hiker sends at most a few SOS messages per trip."
  ranges = {
    trip_duration     = { min = 0, max = 12, unit = "hours" }
    region_pack_size  = { min = 1, max = 500, unit = "MB" }
    sampling_interval = { min = 1, max = 10, unit = "s" }
  }
}

# ── Owned information ────────────────────────────────────────

state "map_pack" {
  description = "The downloaded vector-tile pack of one region, with its checksum."
}

state "sampling_settings" {
  description = "The sampling interval that the hiker selected, from 1 s to 10 s."
}

state "track_log" {
  description = "The append-only, preallocated file of acknowledged fixes for the current recording."
}

state "emergency_contact" {
  description = "The phone number and name of the person who receives an SOS."
}

state "forecast_snapshot" {
  description = "The last fetched forecast for the trailhead coordinates, with its issue time."
}

# ── Level 1: root FRs and DPs ────────────────────────────────

fr "show_map" {
  alias     = "FR1"
  need      = [need.navigate_offline]
  statement = "Show the trail map of a downloaded region without a network connection."
  criterion "offline_render" {
    statement = "Rendering a downloaded region uses no network."
    metric    = "network requests made while rendering a downloaded region"
    op        = "=="
    value     = 0
    unit      = "requests"
    origin    = "proposed"
  }
  criterion "first_render" {
    metric = "time from opening a downloaded region to the first rendered map"
    op     = "<="
    value  = 2
    unit   = "s"
    origin = "proposed"
  }
}

fr "record_track" {
  alias     = "FR2"
  need      = [need.keep_a_record]
  statement = "Record the route that the hiker walks."
  criterion "stored_gap" {
    statement = "The stored track has no gap longer than 15 s during an uninterrupted recording."
    metric    = "maximum time between consecutive stored fixes during an uninterrupted recording"
    op        = "<="
    value     = 15
    unit      = "s"
    origin    = "proposed"
  }
}

fr "send_sos" {
  alias     = "FR3"
  need      = [need.get_help]
  statement = "Send the hiker's position to the emergency contact when the hiker asks for help."
  criterion "handoff_time" {
    metric = "time from SOS confirmation to SMS handoff to the operating system"
    op     = "<="
    value  = 10
    unit   = "s"
    origin = "proposed"
  }
}

fr "show_forecast" {
  alias     = "FR4"
  need      = [need.plan_for_weather]
  statement = "Show the forecast for the trailhead together with its issue time."
  criterion "stale_label" {
    statement = "Every displayed forecast older than 24 hours carries a stale label."
    metric    = "share of displayed forecasts older than 24 hours that carry a stale label"
    op        = "=="
    value     = 1
    unit      = "ratio"
    origin    = "proposed"
  }
}

dp "map_pack_renderer" {
  alias          = "DP1"
  controls       = [fr.show_map]
  responsibility = "Download a region as one checksummed vector-tile pack while online. Render the map only from that local pack."
  decision       = "selected"
  owns_state     = [state.map_pack]
  bounded_by     = [constraint.offline_first, constraint.on_device_only]
}

dp "track_recorder" {
  alias          = "DP2"
  controls       = [fr.record_track]
  responsibility = "Record the walk as a pipeline of two parts: a sampling policy accepts location fixes, and an append-only log stores them. The recorder defines the Fix record that both parts use."
  decision       = "selected"
  role           = "parent"
  bounded_by     = [constraint.offline_first, constraint.on_device_only]
}

dp "sos_beacon" {
  alias          = "DP3"
  controls       = [fr.send_sos]
  responsibility = "Build each SOS from the beacon's own position request, not from the track, and hand one SMS to the operating system. The beacon defines the PositionResult record that its two parts use."
  decision       = "selected"
  role           = "parent"
  why            = "An alternative read the last track point. It was rejected because the track sampling interval would then change the position in the SOS, which couples the SOS to the track recorder."
  bounded_by     = [constraint.offline_first, constraint.on_device_only]
}

dp "forecast_cache" {
  alias          = "DP4"
  controls       = [fr.show_forecast]
  responsibility = "Fetch the forecast for the trailhead coordinates when online. Store it with its issue time. Label it stale when it is older than 24 hours."
  decision       = "selected"
  owns_state     = [state.forecast_snapshot]
  bounded_by     = [constraint.on_device_only]
}

# ── Level 2 inside DP2: track recorder ───────────────────────

fr "sample_position" {
  alias     = "FR2.1"
  parent    = dp.track_recorder
  statement = "Accept location fixes often enough that the walked route has no long gap."
  criterion "accepted_gap" {
    metric = "maximum time between consecutive accepted fixes while recording"
    op     = "<="
    value  = 15
    unit   = "s"
    origin = "proposed"
  }
}

fr "persist_fixes" {
  alias     = "FR2.2"
  parent    = dp.track_recorder
  statement = "Keep every acknowledged fix when the app process stops unexpectedly."
  criterion "no_lost_fix" {
    metric = "acknowledged fixes missing from the track log after the app process is killed"
    op     = "=="
    value  = 0
    unit   = "fixes"
    origin = "proposed"
  }
}

dp "sampling_policy" {
  alias          = "DP2.1"
  controls       = [fr.sample_position]
  responsibility = "Subscribe to the location service at the hiker's interval. Drop a fix that is less accurate than 50 m, unless 15 s have passed since the last accepted fix. Stop sampling below 15 % battery so that the recorder cannot drain the battery that the SOS needs."
  decision       = "selected"
  owns_state     = [state.sampling_settings]
  bounded_by     = [constraint.sampling_range]
}

dp "fix_log" {
  alias          = "DP2.2"
  controls       = [fr.persist_fixes]
  responsibility = "Append each fix to a file preallocated for 12 hours at the 1 s minimum interval, flush the file, and then acknowledge the fix."
  decision       = "selected"
  owns_state     = [state.track_log]
  bounded_by     = [constraint.sampling_range]
  holds_if       = [assumption.preallocation_honored]
}

# ── Level 2 inside DP3: SOS beacon ───────────────────────────

fr "obtain_fix" {
  alias     = "FR3.1"
  parent    = dp.sos_beacon
  statement = "Produce a position result, with its accuracy and age, for the SOS message."
  criterion "result_time" {
    statement = "The result is a fix or an explicit no-fix result, and it always states accuracy and age when it has a fix."
    metric    = "time from SOS confirmation to a position result"
    op        = "<="
    value     = 8
    unit      = "s"
    origin    = "proposed"
  }
}

fr "deliver_message" {
  alias     = "FR3.2"
  parent    = dp.sos_beacon
  statement = "Hand the SOS message for the stored contact to the operating system."
  criterion "dispatch_time" {
    metric = "time from a ready position result to SMS handoff to the operating system"
    op     = "<="
    value  = 2
    unit   = "s"
    origin = "proposed"
  }
}

dp "fix_acquirer" {
  alias          = "DP3.1"
  controls       = [fr.obtain_fix]
  responsibility = "Request one high-accuracy fix with a 7 s timeout. On timeout, use the operating system's last known fix. With neither, return an explicit no-fix result."
  decision       = "selected"
  owns_state     = []
  holds_if       = [assumption.location_service_shared]
}

dp "sms_dispatcher" {
  alias          = "DP3.2"
  controls       = [fr.deliver_message]
  responsibility = "Fill a fixed message template with any position result, including no-fix, and hand exactly one SMS per confirmation to the operating system for the stored contact."
  decision       = "selected"
  owns_state     = [state.emergency_contact]
}

# ── Influences: diagonal (material) ──────────────────────────

influence {
  from      = [dp.map_pack_renderer]
  to        = fr.show_map
  effect    = "material"
  mechanism = "The renderer reads only the local pack, so its pack format and render path decide whether the map appears offline and how fast."
}

influence {
  from      = [dp.track_recorder]
  to        = fr.record_track
  effect    = "material"
  mechanism = "The recorder pipeline decides which fixes are stored and when."
}

influence {
  from      = [dp.sos_beacon]
  to        = fr.send_sos
  effect    = "material"
  mechanism = "The beacon's position request and SMS handoff make up the whole time from confirmation to handoff."
}

influence {
  from      = [dp.forecast_cache]
  to        = fr.show_forecast
  effect    = "material"
  mechanism = "The cache stores the issue time and applies the 24-hour stale rule to every displayed forecast."
}

influence {
  from      = [dp.sampling_policy]
  to        = fr.sample_position
  effect    = "material"
  mechanism = "The interval and the accuracy filter decide which fixes are accepted and how far apart they are."
}

influence {
  from      = [dp.fix_log]
  to        = fr.persist_fixes
  effect    = "material"
  mechanism = "Flushing before acknowledging decides whether an acknowledged fix survives a killed process."
}

influence {
  from      = [dp.fix_acquirer]
  to        = fr.obtain_fix
  effect    = "material"
  mechanism = "The 7 s timeout and the last-known fallback bound the time to a position result."
}

influence {
  from      = [dp.sms_dispatcher]
  to        = fr.deliver_message
  effect    = "material"
  mechanism = "The template fill and the single handoff call make up the dispatch time."
}

# ── Influences: justified zeros, root rows ───────────────────

influence {
  from = [
    dp.track_recorder, dp.sos_beacon, dp.forecast_cache,
    dp.sampling_policy, dp.fix_log, dp.fix_acquirer, dp.sms_dispatcher,
  ]
  to      = fr.show_map
  effect  = "none"
  because = "The renderer reads only the map pack, which no other module writes, and it makes no network request. The track overlay is drawn by the app shell on top of the finished map, so recorder choices cannot change whether or how fast the map renders."
}

influence {
  from     = [dp.map_pack_renderer]
  to       = fr.record_track
  effect   = "none"
  because  = "A region download writes to device storage, but the fix log reserved its whole file before recording started, so a download cannot fill the space that the track needs."
  holds_if = [assumption.preallocation_honored]
}

influence {
  from     = [dp.sos_beacon]
  to       = fr.record_track
  effect   = "none"
  because  = "One SOS position request runs beside the recorder's subscription. It does not stop or delay the recorder's location updates."
  holds_if = [assumption.location_service_shared]
}

influence {
  from    = [dp.forecast_cache]
  to      = fr.record_track
  effect  = "none"
  because = "The forecast cache writes only its own snapshot and uses the network, not the location service or the track log."
}

influence {
  from     = [dp.track_recorder]
  to       = fr.send_sos
  effect   = "none"
  because  = "The beacon takes its position from its own request, not from the track. Track sampling can refresh the operating system's last known fix, which changes the reported age, but the 7 s timeout and the dispatch step fix the 10 s handoff time whatever the recorder does."
  holds_if = [assumption.location_service_shared]
}

influence {
  from    = [dp.map_pack_renderer, dp.forecast_cache]
  to      = fr.send_sos
  effect  = "none"
  because = "The map and the forecast never touch the location service, the emergency contact, or the SMS handoff."
}

influence {
  from = [
    dp.map_pack_renderer, dp.track_recorder, dp.sos_beacon,
    dp.sampling_policy, dp.fix_log, dp.fix_acquirer, dp.sms_dispatcher,
  ]
  to      = fr.show_forecast
  effect  = "none"
  because = "The stale label depends only on the stored issue time and the clock. No other module writes the forecast snapshot."
}

# ── Influences: justified zeros, track recorder rows ─────────

influence {
  from    = [dp.fix_log]
  to      = fr.sample_position
  effect  = "none"
  because = "The recorder hands fixes to the log asynchronously. A slow write delays the acknowledgement, not the sampler's next fix or its accuracy filter."
}

influence {
  from     = [dp.fix_acquirer]
  to       = fr.sample_position
  effect   = "none"
  because  = "An SOS fix request runs beside the sampler's subscription and does not change the sampler's update rate."
  holds_if = [assumption.location_service_shared]
}

influence {
  from    = [dp.map_pack_renderer, dp.sms_dispatcher, dp.forecast_cache]
  to      = fr.sample_position
  effect  = "none"
  because = "These modules do not use the location service or the sampling settings."
}

influence {
  from    = [dp.sampling_policy]
  to      = fr.persist_fixes
  effect  = "none"
  because = "The log is preallocated for the 1 s minimum interval over 12 hours, so every permitted interval fits. The log stores every fix it receives, whatever the accuracy filter accepted."
}

influence {
  from     = [dp.map_pack_renderer]
  to       = fr.persist_fixes
  effect   = "none"
  because  = "A region download cannot take the preallocated space of the log."
  holds_if = [assumption.preallocation_honored]
}

influence {
  from    = [dp.fix_acquirer, dp.sms_dispatcher, dp.forecast_cache]
  to      = fr.persist_fixes
  effect  = "none"
  because = "These modules write no file in the track log's space and do not hold the log's file handle."
}

# ── Influences: justified zeros, SOS beacon rows ─────────────

influence {
  from    = [dp.sms_dispatcher]
  to      = fr.obtain_fix
  effect  = "none"
  because = "The dispatcher runs only after the position result is ready, so it cannot change the time to that result."
}

influence {
  from     = [dp.sampling_policy]
  to       = fr.obtain_fix
  effect   = "none"
  because  = "The sampler's subscription can make the last known fix fresher, which changes the reported age, but the 7 s timeout bounds the result time whatever the sampler does."
  holds_if = [assumption.location_service_shared]
}

influence {
  from    = [dp.map_pack_renderer, dp.fix_log, dp.forecast_cache]
  to      = fr.obtain_fix
  effect  = "none"
  because = "These modules do not use the location service."
}

influence {
  from    = [dp.fix_acquirer]
  to      = fr.deliver_message
  effect  = "none"
  because = "Dispatch time is measured from a ready position result. The template accepts every result, including no-fix, so the acquirer's timeout or fallback cannot change it."
}

influence {
  from    = [dp.map_pack_renderer, dp.sampling_policy, dp.fix_log, dp.forecast_cache]
  to      = fr.deliver_message
  effect  = "none"
  because = "These modules do not read the emergency contact or call the SMS handoff."
}

# ── Requested assertions ─────────────────────────────────────

expect "root_uncoupled" {
  scope          = design.trailhead
  classification = "uncoupled"
  basis          = "conditional"
}

expect "recorder_uncoupled" {
  scope          = dp.track_recorder
  classification = "uncoupled"
  basis          = "conditional"
}

expect "beacon_uncoupled" {
  scope          = dp.sos_beacon
  classification = "uncoupled"
  basis          = "conditional"
}

# ── Process domain: realizations ─────────────────────────────

pv "tile_pack_renderer" {
  alias    = "PV1"
  realizes = [dp.map_pack_renderer]
  kind     = "source unit"
  address  = "src/dp1_map_pack_renderer/pv1_tile_pack_renderer"
}

pv "fix_pipeline" {
  alias    = "PV2"
  realizes = [dp.track_recorder]
  kind     = "source unit"
  address  = "src/dp2_track_recorder/pv2_fix_pipeline"
  note     = "Wires the sampler to the log. The Fix record lives in src/dp2_track_recorder/contract."
}

pv "location_sampler" {
  alias    = "PV2.1"
  realizes = [dp.sampling_policy]
  kind     = "source unit"
  address  = "src/dp2_track_recorder/dp2_1_sampling_policy/pv2_1_location_sampler"
}

pv "preallocated_log" {
  alias    = "PV2.2"
  realizes = [dp.fix_log]
  kind     = "source unit"
  address  = "src/dp2_track_recorder/dp2_2_fix_log/pv2_2_preallocated_log"
}

pv "sos_sequence" {
  alias    = "PV3"
  realizes = [dp.sos_beacon]
  kind     = "source unit"
  address  = "src/dp3_sos_beacon/pv3_sos_sequence"
  note     = "Runs the acquirer and then the dispatcher. The PositionResult record lives in src/dp3_sos_beacon/contract."
}

pv "fix_request" {
  alias    = "PV3.1"
  realizes = [dp.fix_acquirer]
  kind     = "source unit"
  address  = "src/dp3_sos_beacon/dp3_1_fix_acquirer/pv3_1_fix_request"
}

pv "sms_handoff" {
  alias    = "PV3.2"
  realizes = [dp.sms_dispatcher]
  kind     = "source unit"
  address  = "src/dp3_sos_beacon/dp3_2_sms_dispatcher/pv3_2_sms_handoff"
}

pv "forecast_fetcher" {
  alias    = "PV4"
  realizes = [dp.forecast_cache]
  kind     = "source unit"
  address  = "src/dp4_forecast_cache/pv4_forecast_fetcher"
}

# ── Modules ──────────────────────────────────────────────────

module "trailhead_app" {
  alias    = "M0"
  contains = [module.map_pack_renderer, module.track_recorder, module.sos_beacon, module.forecast_cache]
}

module "track_recorder" {
  alias    = "M2"
  contains = [module.sampling_policy, module.fix_log]
}

module "sos_beacon" {
  alias    = "M3"
  contains = [module.fix_acquirer, module.sms_dispatcher]
}

module "map_pack_renderer" {
  alias             = "M1"
  realizes          = [dp.map_pack_renderer]
  inputs            = ["A region that the hiker selects for download.", "A viewport (center and zoom) from the app shell."]
  outputs           = ["A rendered map layer for the viewport."]
  owns_state        = [state.map_pack]
  dependencies      = []
  invariants        = ["Rendering never makes a network request.", "Only a pack whose checksum matches is used for rendering."]
  failure_behavior  = "When the pack is missing or its checksum fails, show that the region has no offline map and offer a download. Never fetch tiles while rendering."
  acceptance_checks = [fr.show_map.criterion.offline_render, fr.show_map.criterion.first_render, scenario.render_offline]
}

module "sampling_policy" {
  alias             = "M2.1"
  realizes          = [dp.sampling_policy]
  inputs            = ["Location updates from the operating system.", "The battery level from the operating system.", "The interval that the hiker selects."]
  outputs           = ["Accepted fixes in the recorder's Fix record format."]
  owns_state        = [state.sampling_settings]
  dependencies      = []
  invariants        = ["The interval stays from 1 s to 10 s.", "No two consecutive accepted fixes are more than 15 s apart while recording.", "Sampling stops below 15 % battery."]
  failure_behavior  = "When the location service reports no fix, keep the subscription and report a no-signal state. Below 15 % battery, stop sampling and report a paused recording."
  acceptance_checks = [fr.sample_position.criterion.accepted_gap, scenario.sample_under_poor_sky]
}

module "fix_log" {
  alias             = "M2.2"
  realizes          = [dp.fix_log]
  inputs            = ["Fixes in the recorder's Fix record format, passed by the recorder pipeline."]
  outputs           = ["One acknowledgement per durable fix.", "The stored track for review and export."]
  owns_state        = [state.track_log]
  dependencies      = []
  invariants        = ["A fix is acknowledged only after it is flushed.", "The log is append-only during a recording."]
  failure_behavior  = "When preallocation fails, refuse to start the recording and tell the hiker how much space is needed. When a write fails, stop acknowledging and report the recording as interrupted."
  acceptance_checks = [fr.persist_fixes.criterion.no_lost_fix, scenario.kill_during_recording]
}

module "fix_acquirer" {
  alias             = "M3.1"
  realizes          = [dp.fix_acquirer]
  inputs            = ["An SOS confirmation.", "Fixes and the last known fix from the operating system."]
  outputs           = ["One PositionResult: a fix with accuracy and age, or an explicit no-fix result."]
  owns_state        = []
  dependencies      = []
  invariants        = ["Exactly one PositionResult per confirmation.", "A result with a fix always states accuracy and age."]
  failure_behavior  = "When no fix arrives within 7 s and no last known fix exists, return the no-fix result so that the SOS is still sent."
  acceptance_checks = [fr.obtain_fix.criterion.result_time, scenario.sos_in_a_canyon]
}

module "sms_dispatcher" {
  alias             = "M3.2"
  realizes          = [dp.sms_dispatcher]
  inputs            = ["One PositionResult, passed by the beacon sequence."]
  outputs           = ["One SMS handoff to the operating system for the stored contact."]
  owns_state        = [state.emergency_contact]
  dependencies      = []
  invariants        = ["Exactly one handoff per confirmation.", "The message always names the hiker and states either the position or that the position is unknown."]
  failure_behavior  = "When no contact is stored, block the SOS button during setup instead of at the moment of need. When the operating system rejects the handoff, show the message text so that the hiker can send it by hand."
  acceptance_checks = [fr.deliver_message.criterion.dispatch_time, scenario.sos_in_a_canyon]
}

module "forecast_cache" {
  alias             = "M4"
  realizes          = [dp.forecast_cache]
  inputs            = ["The trailhead coordinates.", "Forecast responses from the weather service when online.", "The device clock."]
  outputs           = ["The stored forecast with its issue time and a stale label when it is older than 24 hours."]
  owns_state        = [state.forecast_snapshot]
  dependencies      = []
  invariants        = ["A displayed forecast always shows its issue time.", "A forecast older than 24 hours always carries the stale label."]
  failure_behavior  = "When a fetch fails, keep the previous snapshot and its issue time. Never show a forecast without its issue time."
  acceptance_checks = [fr.show_forecast.criterion.stale_label, scenario.stale_forecast]
}

# ── Runtime flows ────────────────────────────────────────────

flow "record_walk" {
  owner  = module.track_recorder
  input  = "Location updates while a recording is active."
  steps  = [module.sampling_policy, module.fix_log]
  output = "Acknowledged fixes in the track log."
}

flow "send_help" {
  owner  = module.sos_beacon
  input  = "An SOS confirmation from the hiker."
  steps  = [module.fix_acquirer, module.sms_dispatcher]
  output = "One SMS handed to the operating system."
}

flow "open_trail_screen" {
  owner  = module.trailhead_app
  input  = "The hiker opens the trail screen."
  steps  = [[module.map_pack_renderer, module.forecast_cache]]
  output = "The map and the forecast side by side, each from its own state."
}

# ── Acceptance scenarios ─────────────────────────────────────

scenario "render_offline" {
  kind        = "operational"
  verifies    = [fr.show_map.criterion.offline_render, fr.show_map.criterion.first_render]
  description = "Covers rendering of a downloaded 500 MB region with the network off."
  steps = [
    "Download a 500 MB region pack while online.",
    "Turn off all networks and record every network request the app makes.",
    "Open the region and expect the first map within 2 s and zero network requests.",
    "Corrupt the pack and expect the no-offline-map message and zero network requests.",
  ]
}

scenario "sample_under_poor_sky" {
  kind        = "operational"
  verifies    = [fr.sample_position.criterion.accepted_gap]
  description = "Covers the accuracy filter when most fixes are worse than 50 m."
  steps = [
    "Replay a location trace at a 1 s interval in which 90 % of fixes are worse than 50 m.",
    "Repeat at the 10 s interval.",
    "Expect no gap between consecutive accepted fixes longer than 15 s in either run.",
  ]
}

scenario "kill_during_recording" {
  kind        = "failure"
  verifies    = [fr.persist_fixes.criterion.no_lost_fix, fr.record_track.criterion.stored_gap]
  description = "Covers a killed process during a recording and the stored-gap target of the parent."
  steps = [
    "Record at the 1 s interval and kill the app process at a random time.",
    "Restart the app and compare the log with the list of acknowledged fixes.",
    "Expect zero acknowledged fixes missing and no stored gap longer than 15 s before the kill.",
  ]
}

scenario "sos_in_a_canyon" {
  kind        = "operational"
  verifies    = [fr.obtain_fix.criterion.result_time, fr.deliver_message.criterion.dispatch_time, fr.send_sos.criterion.handoff_time]
  description = "Covers a fresh fix, the last-known fallback, and the no-fix result."
  steps = [
    "Confirm an SOS with a good sky and expect a fix with accuracy and age within 8 s.",
    "Block new fixes and confirm an SOS. Expect the last known fix within 8 s.",
    "Clear the last known fix and confirm an SOS. Expect the no-fix result within 8 s.",
    "In each run, expect exactly one SMS handoff within 2 s of the result and within 10 s of confirmation.",
  ]
}

scenario "stale_forecast" {
  kind        = "operational"
  verifies    = [fr.show_forecast.criterion.stale_label]
  description = "Covers forecasts just under and just over 24 hours old."
  steps = [
    "Store a forecast issued 23 hours ago and expect no stale label.",
    "Advance the clock past 24 hours and expect the stale label.",
    "Fail the next fetch and expect the old snapshot with its issue time and the stale label.",
  ]
}

scenario "change_sampling_interval" {
  kind              = "change"
  vary              = [dp.sampling_policy]
  expect_affected   = [fr.sample_position]
  expect_unaffected = [fr.persist_fixes, fr.obtain_fix, fr.deliver_message, fr.show_map, fr.show_forecast]
  description       = "Tests the diagonal claim for the sampler, including the location-service and storage zeros."
  steps = [
    "Run every leaf scenario at the 1 s interval and again at the 10 s interval.",
    "Expect only the accepted-gap measurements to change.",
  ]
}

scenario "large_download_while_recording" {
  kind              = "change"
  vary              = [dp.map_pack_renderer]
  expect_affected   = [fr.show_map]
  expect_unaffected = [fr.persist_fixes, fr.sample_position]
  description       = "Tests the storage zero: a region download must not take the log's space."
  steps = [
    "Fill the device until only the log's reserved space and 500 MB remain.",
    "Start a recording, then download a 500 MB region.",
    "Expect the download to fail for lack of space and zero acknowledged fixes missing from the log.",
  ]
}
