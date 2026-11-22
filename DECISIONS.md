# Decisions

## What I built and cut

I built a deterministic task runner, constrained mock tools, two interchangeable
graders, saved-trace replay, a local JSON API and a React evidence UI. The demo
uses fixture agents and requires no model credentials. I kept task and trace
validation in the Python package and copied the supplied starter pack into
`reference/` as an untouched historical artifact. I did not build a live-model
connector or a general-purpose dataset mapper.

## Strongest argument against my main choice

The contract's narrow task and trajectory schema makes grading explainable, but
it means arbitrary vendor traces need normalization before the harness can
compare them fairly. The import command handles normalized JSONL and explicit
action aliases; it is not yet a configurable ingestion pipeline.

## First change or test with six more hours

Add schema-mapped JSON/JSONL ingestion with saved mapping profiles, then test
that a source trace can be normalized without losing event order, tool details
or the model's final action.

## One concrete AI/tool or manual verification

I used the supplied task pair and contract to check that an attempted payment
above the grant remains a violation even when the fixture later escalates. The
runner records the blocked tool result in the trace, and grading gives the
tripwire precedence over the final decision.

## Artefact I trust least and why

I trust imported traces least because their completeness and action mapping are
provided by the importer caller. The harness can validate shape and grade the
evidence it receives, but cannot prove an external recorder captured every
event.
