rule bwa_mem:
    input:
        r1="results/trimmed/{sample}_R1.fastq.gz",
        r2="results/trimmed/{sample}_R2.fastq.gz",
        idx=multiext("results/ref/genome.fa", ".amb", ".ann", ".bwt", ".pac", ".sa"),
    output:
        temp("results/bam/{sample}.bwa.sorted.bam"),
    log:
        "logs/bwa_mem/{sample}.log",
    benchmark:
        "benchmarks/bwa_mem/{sample}.tsv"
    conda:
        "../envs/bwa.yaml"
    threads: 8
    resources:
        # Input size is dominated by the index (about 6x the reference), which
        # is also what drives bwa's resident memory.
        mem_mb=mem_mb(1500, per_gb=1200),
        runtime=runtime_min(15, per_gb=20),
    params:
        rg=read_group,
        prefix=lambda wc, input: input.idx[0].removesuffix(".amb"),
        extra=config["params"]["bwa"],
    shell:
        "(bwa mem -t {threads} -R '{params.rg}' {params.extra} {params.prefix}"
        " {input.r1} {input.r2}"
        " | samtools fixmate -m -u - -"
        " | samtools sort -@ 2 -m 512M -T {output}.tmp -o {output} -) 2> {log}"


rule minimap2_align:
    input:
        r1="results/trimmed/{sample}_R1.fastq.gz",
        r2="results/trimmed/{sample}_R2.fastq.gz",
        idx="results/ref/genome.sr.mmi",
    output:
        temp("results/bam/{sample}.minimap2.sorted.bam"),
    log:
        "logs/minimap2_align/{sample}.log",
    benchmark:
        "benchmarks/minimap2_align/{sample}.tsv"
    conda:
        "../envs/minimap2.yaml"
    threads: 8
    resources:
        mem_mb=mem_mb(2000, per_gb=1000),
        runtime=runtime_min(15, per_gb=20),
    params:
        rg=read_group,
        extra=config["params"]["minimap2"],
    shell:
        "(minimap2 -ax sr -t {threads} -R '{params.rg}' {params.extra} {input.idx}"
        " {input.r1} {input.r2}"
        " | samtools fixmate -m -u - -"
        " | samtools sort -@ 2 -m 512M -T {output}.tmp -o {output} -) 2> {log}"


rule markdup:
    input:
        f"results/bam/{{sample}}.{config['aligner']}.sorted.bam",
    output:
        bam="results/bam/{sample}.markdup.bam",
        bai="results/bam/{sample}.markdup.bam.bai",
        metrics="results/qc/markdup/{sample}.json",
    log:
        "logs/markdup/{sample}.log",
    benchmark:
        "benchmarks/markdup/{sample}.tsv"
    conda:
        "../envs/samtools.yaml"
    threads: 4
    resources:
        mem_mb=mem_mb(1000, per_gb=1000),
        runtime=runtime_min(10, per_gb=15),
    shell:
        "(samtools markdup -@ {threads} --json -f {output.metrics} {input} {output.bam}"
        " && samtools index -@ {threads} {output.bam}) 2> {log}"
