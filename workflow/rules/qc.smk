rule fastp:
    input:
        unpack(get_fastqs),
    output:
        r1=temp("results/trimmed/{sample}_R1.fastq.gz"),
        r2=temp("results/trimmed/{sample}_R2.fastq.gz"),
        html="results/qc/fastp/{sample}.html",
        json="results/qc/fastp/{sample}.json",
    log:
        "logs/fastp/{sample}.log",
    benchmark:
        "benchmarks/fastp/{sample}.tsv"
    conda:
        "../envs/fastp.yaml"
    threads: 4
    resources:
        mem_mb=mem_mb(1000, per_gb=500),
        runtime=runtime_min(10, per_gb=10),
    params:
        extra=config["params"]["fastp"],
    shell:
        "fastp --in1 {input.r1} --in2 {input.r2} --out1 {output.r1} --out2 {output.r2}"
        " --html {output.html} --json {output.json} --thread {threads} {params.extra}"
        " 2> {log}"


rule samtools_stats:
    input:
        bam="results/bam/{sample}.markdup.bam",
        bai="results/bam/{sample}.markdup.bam.bai",
        ref="results/ref/genome.fa",
        regions="results/ref/regions.bed",
    output:
        "results/qc/samtools_stats/{sample}.txt",
    log:
        "logs/samtools_stats/{sample}.log",
    benchmark:
        "benchmarks/samtools_stats/{sample}.tsv"
    conda:
        "../envs/samtools.yaml"
    threads: 2
    resources:
        mem_mb=mem_mb(500, per_gb=200),
    shell:
        "samtools stats -@ {threads} -r {input.ref} -t {input.regions} {input.bam}"
        " > {output} 2> {log}"


rule mosdepth:
    input:
        bam="results/bam/{sample}.markdup.bam",
        bai="results/bam/{sample}.markdup.bam.bai",
        regions="results/ref/regions.bed",
    output:
        summary="results/qc/mosdepth/{sample}.mosdepth.summary.txt",
        dist="results/qc/mosdepth/{sample}.mosdepth.region.dist.txt",
        regions="results/qc/mosdepth/{sample}.regions.bed.gz",
    log:
        "logs/mosdepth/{sample}.log",
    benchmark:
        "benchmarks/mosdepth/{sample}.tsv"
    conda:
        "../envs/mosdepth.yaml"
    threads: 2
    resources:
        mem_mb=mem_mb(500, per_gb=500),
    params:
        prefix=lambda wc, output: output.summary.removesuffix(".mosdepth.summary.txt"),
        extra=config["params"]["mosdepth"],
    shell:
        "mosdepth --threads {threads} --by {input.regions} {params.extra}"
        " {params.prefix} {input.bam} 2> {log}"


rule qc_summary:
    input:
        fastp=expand("results/qc/fastp/{sample}.json", sample=SAMPLES),
        stats=expand("results/qc/samtools_stats/{sample}.txt", sample=SAMPLES),
        mosdepth=expand(
            "results/qc/mosdepth/{sample}.mosdepth.summary.txt", sample=SAMPLES
        ),
    output:
        report(
            "results/qc/qc_summary.tsv",
            caption="../report/qc_summary.rst",
            category="1. Read and alignment QC",
        ),
    log:
        "logs/qc_summary.log",
    conda:
        "../envs/python.yaml"
    params:
        samples=SAMPLES,
    script:
        "../scripts/qc_summary.py"
