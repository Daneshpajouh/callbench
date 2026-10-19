Germline small-variant calls for {{ snakemake.config["samples"] }} were made with
the callers {{ snakemake.config["callers"] | join(", ") }} after alignment with
{{ snakemake.config["aligner"] }}, then compared with Genome in a Bottle v4.2.1
truth using RTG vcfeval inside the truth-set confident regions that overlap the
evaluation intervals in {{ snakemake.config["regions"] }}.

Calling was scattered into chunks of at most {{ snakemake.config["scatter"]["chunk_size"] }} bp
and gathered per sample and caller. Calls failing the per-caller filter in
``config["filters"]`` were dropped before evaluation.
