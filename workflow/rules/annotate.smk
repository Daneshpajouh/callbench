rule clinvar_subset:
    """ClinVar records inside the evaluation intervals, renamed to chr contigs.

    ClinVar names contigs 1..22, X, Y, MT while the GIAB reference uses chr1..
    The subset is taken first so the rename touches a few thousand records, not
    the whole file.
    """
    input:
        vcf=config["clinvar"]["vcf"],
        regions="results/ref/regions.bed",
    output:
        vcf="results/annotation/clinvar.regions.vcf.gz",
        tbi="results/annotation/clinvar.regions.vcf.gz.tbi",
        chrmap=temp("results/annotation/clinvar.chrmap.txt"),
        nochr=temp("results/annotation/regions.nochr.bed"),
    log:
        "logs/clinvar_subset.log",
    conda:
        "../envs/bcftools.yaml"
    shell:
        "(for c in $(seq 1 22) X Y; do printf '%s\\tchr%s\\n' $c $c; done > {output.chrmap}"
        " && printf 'MT\\tchrM\\n' >> {output.chrmap}"
        " && sed 's/^chr//' {input.regions} > {output.nochr}"
        " && bcftools view -R {output.nochr} -Ou {input.vcf}"
        " | bcftools annotate --rename-chrs {output.chrmap} -Oz -o {output.vcf}"
        " && bcftools index -t {output.vcf}) 2> {log}"


rule annotate_clinvar:
    input:
        vcf="results/calls/{sample}/{caller}.norm.vcf.gz",
        tbi="results/calls/{sample}/{caller}.norm.vcf.gz.tbi",
        clinvar="results/annotation/clinvar.regions.vcf.gz",
        clinvar_tbi="results/annotation/clinvar.regions.vcf.gz.tbi",
    output:
        vcf="results/annotated/{sample}/{caller}.clinvar.vcf.gz",
        tbi="results/annotated/{sample}/{caller}.clinvar.vcf.gz.tbi",
    log:
        "logs/annotate_clinvar/{sample}.{caller}.log",
    benchmark:
        "benchmarks/annotate_clinvar/{sample}.{caller}.tsv"
    conda:
        "../envs/bcftools.yaml"
    shell:
        # Match on CHROM, POS, REF and ALT, so a ClinVar record only lands on a
        # call with the same allele, not on any call at that position.
        "(bcftools annotate -a {input.clinvar} -c ID,INFO/CLNSIG,INFO/CLNREVSTAT,"
        "INFO/CLNDN,INFO/GENEINFO,INFO/ALLELEID --pair-logic exact"
        " -Oz -o {output.vcf} {input.vcf}"
        " && bcftools index -t {output.vcf}) 2> {log}"


rule clinvar_table:
    input:
        "results/annotated/{sample}/{caller}.clinvar.vcf.gz",
    output:
        "results/annotated/{sample}/{caller}.clinvar.tsv",
    log:
        "logs/clinvar_table/{sample}.{caller}.log",
    conda:
        "../envs/bcftools.yaml"
    shell:
        "(printf 'chrom\\tpos\\tref\\talt\\tgt\\tclinvar_id\\tclnsig\\tclnrevstat\\tgeneinfo\\n'"
        " && bcftools query -i 'INFO/CLNSIG!=\".\"'"
        " -f '%CHROM\\t%POS\\t%REF\\t%ALT\\t[%GT]\\t%ID\\t%INFO/CLNSIG\\t%INFO/CLNREVSTAT"
        "\\t%INFO/GENEINFO\\n' {input}) > {output} 2> {log}"
