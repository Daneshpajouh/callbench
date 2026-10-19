rule confident_regions:
    """Truth-set confident regions restricted to the evaluation intervals."""
    input:
        truth_bed=lambda wc: get_truth(wc)["bed"],
        regions="results/ref/regions.bed",
    output:
        "results/evaluation/{sample}/confident_regions.bed",
    log:
        "logs/confident_regions/{sample}.log",
    localrule: True
    conda:
        "../envs/python.yaml"
    script:
        "../scripts/intersect_bed.py"


rule stratum_regions:
    """GIAB stratification BED restricted to the evaluation intervals."""
    input:
        truth_bed=lambda wc: config["evaluation"]["stratifications"][wc.stratum],
        regions="results/ref/regions.bed",
    output:
        "results/evaluation/strata/{stratum}.bed",
    log:
        "logs/stratum_regions/{stratum}.log",
    localrule: True
    conda:
        "../envs/python.yaml"
    script:
        "../scripts/intersect_bed.py"


rule vcfeval:
    input:
        calls="results/calls/{sample}/{caller}.norm.vcf.gz",
        calls_tbi="results/calls/{sample}/{caller}.norm.vcf.gz.tbi",
        truth=lambda wc: get_truth(wc)["vcf"],
        bed="results/evaluation/{sample}/confident_regions.bed",
        sdf="results/ref/genome.sdf",
    output:
        summary="results/evaluation/{sample}/{caller}/vcfeval/summary.txt",
        tp="results/evaluation/{sample}/{caller}/vcfeval/tp.vcf.gz",
        tp_base="results/evaluation/{sample}/{caller}/vcfeval/tp-baseline.vcf.gz",
        fp="results/evaluation/{sample}/{caller}/vcfeval/fp.vcf.gz",
        fn="results/evaluation/{sample}/{caller}/vcfeval/fn.vcf.gz",
    log:
        "logs/vcfeval/{sample}.{caller}.log",
    benchmark:
        "benchmarks/vcfeval/{sample}.{caller}.tsv"
    conda:
        "../envs/evaluation.yaml"
    threads: 2
    resources:
        mem_mb=mem_mb(3000, per_gb=1000),
    params:
        outdir=lambda wc, output: os.path.dirname(output.summary),
        extra=config["params"]["vcfeval"],
    shell:
        # vcfeval refuses to write into an existing directory, and Snakemake
        # creates the output directory before the job starts.
        "rm -rf {params.outdir} && RTG_MEM=$(({resources.mem_mb} * 8 / 10))m"
        " rtg vcfeval -b {input.truth} -c {input.calls} -t {input.sdf}"
        " --evaluation-regions {input.bed} --threads {threads} {params.extra}"
        " -o {params.outdir} > {log} 2>&1"


rule stratified_metrics:
    input:
        tp="results/evaluation/{sample}/{caller}/vcfeval/tp.vcf.gz",
        tp_base="results/evaluation/{sample}/{caller}/vcfeval/tp-baseline.vcf.gz",
        fp="results/evaluation/{sample}/{caller}/vcfeval/fp.vcf.gz",
        fn="results/evaluation/{sample}/{caller}/vcfeval/fn.vcf.gz",
        bed="results/evaluation/{sample}/confident_regions.bed",
        strata=expand("results/evaluation/strata/{stratum}.bed", stratum=STRATA),
    output:
        "results/evaluation/{sample}/{caller}/stratified_metrics.tsv",
    log:
        "logs/stratified_metrics/{sample}.{caller}.log",
    benchmark:
        "benchmarks/stratified_metrics/{sample}.{caller}.tsv"
    conda:
        "../envs/evaluation.yaml"
    params:
        strata=STRATA,
    script:
        "../scripts/stratified_metrics.py"
