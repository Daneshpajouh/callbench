# Roadmap

Milestones after v1.0.0, in order. Each is written as user stories with
acceptance criteria that can be checked by running something. Nothing listed
here exists in the code yet.

## M1 (v1.1.0): maintenance experiment, upgrade one caller

As the maintainer of a production pipeline, I want a recorded procedure for
upgrading a caller, so that version bumps are decided on measured accuracy
and resources rather than on release notes.

Acceptance criteria:

* Done on 2026-10-19 for bcftools 1.23.1 to 1.24
  (`docs/changes/2026-10-19-bcftools-1.24.md`); repeat for FreeBayes when a
  release after 1.3.10 appears.
* Full-size HG002 run repeated; `accuracy.tsv` and `profiling.by_rule.tsv`
  compared with v1.0.0 in a short change record under `docs/changes/` that
  states the decision (adopt or hold) and the rollback steps (revert the env
  file, delete the matching `.snakemake/conda/<hash>` folder, rerun from
  `normalise`).
* `.tests/expected_accuracy.tsv` updated in the same pull request if the
  numbers moved, with the reason in the PR description.
* `profiling_table` fails when every `max_rss` value is NA (action item from
  the macOS benchmark postmortem).
* FreeBayes run-to-run indel difference (one record) explained, starting with
  fastp at one thread.
* Per-rule tests from `--generate-unit-tests` kept under 5 MB and 60 s.

## M2 (v1.2.0): HG001, HG003 and HG004 cohort run

As an operator, I want the four-sample cohort run from one samplesheet, so
that accuracy is reported across genomes and not from one sample.

Acceptance criteria:

* `config/samples.tsv` lists HG001 to HG004; the reads and truth sets are
  already fetched and hashed (`docs/data_sources.md`).
* `accuracy.tsv` has rows for all four samples and both callers; the report
  figure shows the spread across samples.
* Per-sample CPU-hours and peak memory added to `docs/capacity_planning.md`.

## M3 (v1.3.0): GATK HaplotypeCaller and DeepVariant adapters

As a reviewer of caller choices, I want the two most common production
callers in the same comparison, so that the default-caller decision covers
them.

Acceptance criteria:

* One adapter rule per caller writing the per-chunk output contract; the
  container image pinned by digest; `container:` used under
  `--sdm apptainer`, a documented `docker run` path for workstations.
* Runtime recorded for native linux/amd64 and for emulated amd64 on Apple
  Silicon, labelled as such.
* `docs/evaluation/caller_evaluation.md` updated with measured numbers.

## M4 (v2.0.0): somatic track on SEQC2 HCC1395

As an analyst who also runs tumour and normal pairs, I want the same
benchmarking for somatic calls, so that somatic callers are chosen on measured
accuracy.

Acceptance criteria:

* Region-restricted HCC1395 (tumour) and HCC1395BL (normal) reads from
  SRA project SRP162370; SEQC2 somatic truth v1.2 high-confidence VCF and
  BED. The NCBI HTTPS host disallows scripts in robots.txt, so a permitted
  route for these files is found and recorded first.
* Strelka2 (with Manta candidate indels) and Mutect2 adapters, evaluated with
  RTG vcfeval in `--squash-ploidy` mode against the SEQC2 truth.
* The somatic track is a separate entry point (`workflow/somatic.smk`) so the
  germline outputs and their contract do not change.

## M5: IPR-shaped germline output

As a reporting team, I want ClinVar-annotated germline calls in the shape of
the public IPR germline upload schema
(`pori_ipr_api` repository, `app/schemas/germlineSmallMutation/upload.js`), so
that the output can be loaded without a hand-written converter.

Acceptance criteria:

* A JSON with top-level `project`, `version`, `source` and `rows`; each row
  with `gene`, `chromosome`, `position`, `reference`, `alteration`,
  `zygosityGermline`, `clinvar` and `clinvarIds` filled from the calls.
  `hgvsCdna` and `hgvsProtein` stay empty until an annotator such as VEP is
  added; nothing is filled by guessing.
* Validated against the schema file from that repository in a unit test.
* Described as shaped to match the public schema; no claim of use by or
  endorsement from any group.
