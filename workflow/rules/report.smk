rule aggregate_accuracy:
    input:
        [
            f"results/evaluation/{s}/{c}/stratified_metrics.tsv"
            for s, c in evaluated_pairs()
        ],
    output:
        report(
            "results/report/accuracy.tsv",
            caption="../report/accuracy.rst",
            category="2. Accuracy against GIAB",
        ),
    log:
        "logs/aggregate_accuracy.log",
    localrule: True
    conda:
        "../envs/python.yaml"
    script:
        "../scripts/aggregate_tables.py"


rule profiling_table:
    """Collect every benchmark directive file into one table.

    Depends on the accuracy table so it runs last and sees the benchmark files
    of every heavy rule in this DAG.
    """
    input:
        accuracy="results/report/accuracy.tsv",
        clinvar="results/report/clinvar_summary.tsv",
        qc="results/qc/qc_summary.tsv",
    output:
        table=report(
            "results/report/profiling.tsv",
            caption="../report/profiling.rst",
            category="3. Runtime and memory",
        ),
        by_rule=report(
            "results/report/profiling.by_rule.tsv",
            caption="../report/profiling_by_rule.rst",
            category="3. Runtime and memory",
        ),
    log:
        "logs/profiling_table.log",
    localrule: True
    conda:
        "../envs/python.yaml"
    params:
        benchmark_dir="benchmarks",
    script:
        "../scripts/profiling_table.py"


rule plots:
    input:
        accuracy="results/report/accuracy.tsv",
        profiling="results/report/profiling.by_rule.tsv",
    output:
        f1=report(
            "results/report/accuracy_f1.svg",
            caption="../report/accuracy_f1.rst",
            category="2. Accuracy against GIAB",
        ),
        runtime=report(
            "results/report/runtime.svg",
            caption="../report/runtime.rst",
            category="3. Runtime and memory",
        ),
    log:
        "logs/plots.log",
    localrule: True
    conda:
        "../envs/python.yaml"
    script:
        "../scripts/plots.py"


rule clinvar_summary:
    input:
        expand(
            "results/annotated/{sample}/{caller}.clinvar.tsv",
            sample=SAMPLES,
            caller=CALLERS,
        ),
    output:
        report(
            "results/report/clinvar_summary.tsv",
            caption="../report/clinvar_summary.rst",
            category="4. ClinVar annotation",
        ),
    log:
        "logs/clinvar_summary.log",
    localrule: True
    conda:
        "../envs/python.yaml"
    script:
        "../scripts/clinvar_summary.py"
