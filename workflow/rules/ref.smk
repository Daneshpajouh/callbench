rule link_reference:
    input:
        config["reference"]["fasta"],
    output:
        "results/ref/genome.fa",
    log:
        "logs/link_reference.log",
    localrule: True
    conda:
        "../envs/samtools.yaml"
    shell:
        "ln -sf $(realpath {input}) {output} 2> {log}"


rule faidx:
    input:
        "results/ref/genome.fa",
    output:
        "results/ref/genome.fa.fai",
    log:
        "logs/faidx.log",
    conda:
        "../envs/samtools.yaml"
    shell:
        "samtools faidx {input} 2> {log}"


rule bwa_index:
    input:
        "results/ref/genome.fa",
    output:
        multiext("results/ref/genome.fa", ".amb", ".ann", ".bwt", ".pac", ".sa"),
    log:
        "logs/bwa_index.log",
    benchmark:
        "benchmarks/bwa_index.tsv"
    conda:
        "../envs/bwa.yaml"
    resources:
        mem_mb=mem_mb(1000, per_gb=6000),
        runtime=runtime_min(10, per_gb=30),
    shell:
        "bwa index {input} 2> {log}"


rule minimap2_index:
    input:
        "results/ref/genome.fa",
    output:
        "results/ref/genome.sr.mmi",
    log:
        "logs/minimap2_index.log",
    benchmark:
        "benchmarks/minimap2_index.tsv"
    conda:
        "../envs/minimap2.yaml"
    resources:
        mem_mb=mem_mb(2000, per_gb=8000),
    shell:
        "minimap2 -x sr -d {output} {input} 2> {log}"


rule rtg_sdf:
    input:
        "results/ref/genome.fa",
    output:
        directory("results/ref/genome.sdf"),
    log:
        "logs/rtg_sdf.log",
    conda:
        "../envs/evaluation.yaml"
    resources:
        mem_mb=4000,
    shell:
        "RTG_MEM={resources.mem_mb}m rtg format -o {output} {input} > {log} 2>&1"


rule evaluation_regions:
    input:
        config["regions"],
    output:
        "results/ref/regions.bed",
    log:
        "logs/evaluation_regions.log",
    localrule: True
    conda:
        "../envs/samtools.yaml"
    shell:
        "sort -k1,1 -k2,2n {input} > {output} 2> {log}"
