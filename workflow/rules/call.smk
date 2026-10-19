checkpoint scatter_intervals:
    input:
        regions="results/ref/regions.bed",
    output:
        directory("results/scatter"),
    log:
        "logs/scatter_intervals.log",
    localrule: True
    conda:
        "../envs/python.yaml"
    params:
        chunk_size=config["scatter"]["chunk_size"],
    script:
        "../scripts/scatter_intervals.py"


# Each caller is an adapter with one output contract: a bgzipped, indexed,
# single-sample VCF per chunk at results/calls/{sample}/{caller}/chunks/.
# Gathering, normalisation, evaluation and annotation never look at which
# caller produced the file.


rule call_bcftools:
    input:
        bam="results/bam/{sample}.markdup.bam",
        bai="results/bam/{sample}.markdup.bam.bai",
        ref="results/ref/genome.fa",
        fai="results/ref/genome.fa.fai",
        bed="results/scatter/{chunk}.bed",
    output:
        vcf=temp("results/calls/{sample}/bcftools/chunks/{chunk}.vcf.gz"),
        tbi=temp("results/calls/{sample}/bcftools/chunks/{chunk}.vcf.gz.tbi"),
    log:
        "logs/call_bcftools/{sample}.{chunk}.log",
    benchmark:
        "benchmarks/call_bcftools/{sample}.{chunk}.tsv"
    conda:
        "../envs/bcftools.yaml"
    resources:
        mem_mb=mem_mb(500, per_gb=200),
        runtime=runtime_min(10, per_gb=30),
    params:
        mpileup=config["params"]["bcftools_mpileup"],
        call=config["params"]["bcftools_call"],
    shell:
        "(bcftools mpileup -f {input.ref} -R {input.bed} {params.mpileup} -Ou {input.bam}"
        " | bcftools call -m -v {params.call} -Ou"
        " | bcftools sort -Oz -o {output.vcf}"
        " && bcftools index -t {output.vcf}) 2> {log}"


rule call_freebayes:
    input:
        bam="results/bam/{sample}.markdup.bam",
        bai="results/bam/{sample}.markdup.bam.bai",
        ref="results/ref/genome.fa",
        fai="results/ref/genome.fa.fai",
        bed="results/scatter/{chunk}.bed",
    output:
        vcf=temp("results/calls/{sample}/freebayes/chunks/{chunk}.vcf.gz"),
        tbi=temp("results/calls/{sample}/freebayes/chunks/{chunk}.vcf.gz.tbi"),
    log:
        "logs/call_freebayes/{sample}.{chunk}.log",
    benchmark:
        "benchmarks/call_freebayes/{sample}.{chunk}.tsv"
    conda:
        "../envs/freebayes.yaml"
    resources:
        mem_mb=mem_mb(1000, per_gb=1000),
        runtime=runtime_min(20, per_gb=120),
    params:
        extra=config["params"]["freebayes"],
    shell:
        "(freebayes -f {input.ref} -t {input.bed} {params.extra} {input.bam}"
        " | bcftools sort -Oz -o {output.vcf}"
        " && bcftools index -t {output.vcf}) 2> {log}"


rule gather_calls:
    input:
        gathered_chunk_vcfs,
    output:
        vcf="results/calls/{sample}/{caller}.raw.vcf.gz",
        tbi="results/calls/{sample}/{caller}.raw.vcf.gz.tbi",
    log:
        "logs/gather_calls/{sample}.{caller}.log",
    benchmark:
        "benchmarks/gather_calls/{sample}.{caller}.tsv"
    conda:
        "../envs/bcftools.yaml"
    resources:
        mem_mb=mem_mb(500, per_gb=200),
    shell:
        # Chunks do not overlap, but a deletion that starts in one chunk can be
        # reported by both neighbours; --allow-overlaps plus --remove-duplicates
        # keeps one copy.
        "(bcftools concat --allow-overlaps --remove-duplicates -Ou {input}"
        " | bcftools sort -Oz -o {output.vcf}"
        " && bcftools index -t {output.vcf}) 2> {log}"


rule normalise:
    input:
        vcf="results/calls/{sample}/{caller}.raw.vcf.gz",
        ref="results/ref/genome.fa",
        fai="results/ref/genome.fa.fai",
        regions="results/ref/regions.bed",
    output:
        vcf="results/calls/{sample}/{caller}.norm.vcf.gz",
        tbi="results/calls/{sample}/{caller}.norm.vcf.gz.tbi",
    log:
        "logs/normalise/{sample}.{caller}.log",
    benchmark:
        "benchmarks/normalise/{sample}.{caller}.tsv"
    conda:
        "../envs/bcftools.yaml"
    resources:
        mem_mb=mem_mb(500, per_gb=200),
    params:
        # FreeBayes emits complex alleles (MNPs and indel/SNV blocks); -a splits
        # them into primitives so they compare like for like with bcftools calls.
        atomize=lambda wc: "--atomize" if wc.caller == "freebayes" else "",
        keep=lambda wc: config["filters"][wc.caller],
    shell:
        "(bcftools view -T {input.regions} -i 'GT~\"1\" && {params.keep}' -Ou {input.vcf}"
        " | bcftools norm -f {input.ref} -m -any {params.atomize} -Ou"
        " | bcftools norm -d exact -Ou"
        " | bcftools sort -Oz -o {output.vcf}"
        " && bcftools index -t {output.vcf}) 2> {log}"
