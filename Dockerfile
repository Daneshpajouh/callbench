FROM condaforge/miniforge3@sha256:f752860f77bd417aa4db35be3d2e906fdb740fb80f40755ed651fff9e8873aad
LABEL io.github.snakemake.containerized="true"
LABEL io.github.snakemake.conda_env_hash="8feac5c729b8c388476ae6f870bc63f36885974c7be9c34c0ee795087bf35b6a"
# Conda environment:
#   source: workflow/envs/bcftools.yaml
#   prefix: /conda-envs/0aa693e4f3299c185685b1e17c70d2ce
#   channels:
#     - conda-forge
#     - bioconda
#     - nodefaults
#   dependencies:
#     - bcftools=1.23.1
RUN mkdir -p /conda-envs/0aa693e4f3299c185685b1e17c70d2ce
COPY workflow/envs/bcftools.yaml /conda-envs/0aa693e4f3299c185685b1e17c70d2ce/environment.yaml
# Conda environment:
#   source: workflow/envs/bwa.yaml
#   prefix: /conda-envs/863ea15d5cdb44d3ed178349d33ff5ce
#   channels:
#     - conda-forge
#     - bioconda
#     - nodefaults
#   dependencies:
#     - bwa=0.7.19
#     - samtools=1.23.1
RUN mkdir -p /conda-envs/863ea15d5cdb44d3ed178349d33ff5ce
COPY workflow/envs/bwa.yaml /conda-envs/863ea15d5cdb44d3ed178349d33ff5ce/environment.yaml
# Conda environment:
#   source: workflow/envs/evaluation.yaml
#   prefix: /conda-envs/16eb2e07c63233721fb979e7b6dd6efb
#   channels:
#     - conda-forge
#     - bioconda
#     - nodefaults
#   dependencies:
#     - rtg-tools=3.13
#     - bcftools=1.23.1
#     - python=3.12
#     - pandas=2.2.3
RUN mkdir -p /conda-envs/16eb2e07c63233721fb979e7b6dd6efb
COPY workflow/envs/evaluation.yaml /conda-envs/16eb2e07c63233721fb979e7b6dd6efb/environment.yaml
# Conda environment:
#   source: workflow/envs/fastp.yaml
#   prefix: /conda-envs/a8d69dac2431227983c93aacf938976a
#   channels:
#     - conda-forge
#     - bioconda
#     - nodefaults
#   dependencies:
#     - fastp=1.4.0
RUN mkdir -p /conda-envs/a8d69dac2431227983c93aacf938976a
COPY workflow/envs/fastp.yaml /conda-envs/a8d69dac2431227983c93aacf938976a/environment.yaml
# Conda environment:
#   source: workflow/envs/freebayes.yaml
#   prefix: /conda-envs/076f410184348693671168900d82ff2d
#   channels:
#     - conda-forge
#     - bioconda
#     - nodefaults
#   dependencies:
#     - freebayes=1.3.10
#     - bcftools=1.21
RUN mkdir -p /conda-envs/076f410184348693671168900d82ff2d
COPY workflow/envs/freebayes.yaml /conda-envs/076f410184348693671168900d82ff2d/environment.yaml
# Conda environment:
#   source: workflow/envs/minimap2.yaml
#   prefix: /conda-envs/1336ed67b92af34851991cb1cb6e9ed7
#   channels:
#     - conda-forge
#     - bioconda
#     - nodefaults
#   dependencies:
#     - minimap2=2.31
#     - samtools=1.23.1
RUN mkdir -p /conda-envs/1336ed67b92af34851991cb1cb6e9ed7
COPY workflow/envs/minimap2.yaml /conda-envs/1336ed67b92af34851991cb1cb6e9ed7/environment.yaml
# Conda environment:
#   source: workflow/envs/mosdepth.yaml
#   prefix: /conda-envs/f3db69b2d9ebd3df3b2cd02edb6533d3
#   channels:
#     - conda-forge
#     - bioconda
#     - nodefaults
#   dependencies:
#     - mosdepth=0.3.14
RUN mkdir -p /conda-envs/f3db69b2d9ebd3df3b2cd02edb6533d3
COPY workflow/envs/mosdepth.yaml /conda-envs/f3db69b2d9ebd3df3b2cd02edb6533d3/environment.yaml
# Conda environment:
#   source: workflow/envs/python.yaml
#   prefix: /conda-envs/2c4320f38dc57a106602f72d77797147
#   channels:
#     - conda-forge
#     - bioconda
#     - nodefaults
#   dependencies:
#     - python=3.12
#     - pandas=2.2.3
#     - matplotlib-base=3.9.2
RUN mkdir -p /conda-envs/2c4320f38dc57a106602f72d77797147
COPY workflow/envs/python.yaml /conda-envs/2c4320f38dc57a106602f72d77797147/environment.yaml
# Conda environment:
#   source: workflow/envs/samtools.yaml
#   prefix: /conda-envs/b7446a759507bd4367cd46bc4bf98c4a
#   channels:
#     - conda-forge
#     - bioconda
#     - nodefaults
#   dependencies:
#     - samtools=1.23.1
RUN mkdir -p /conda-envs/b7446a759507bd4367cd46bc4bf98c4a
COPY workflow/envs/samtools.yaml /conda-envs/b7446a759507bd4367cd46bc4bf98c4a/environment.yaml

RUN conda env create --prefix /conda-envs/0aa693e4f3299c185685b1e17c70d2ce --file /conda-envs/0aa693e4f3299c185685b1e17c70d2ce/environment.yaml && \
    conda env create --prefix /conda-envs/863ea15d5cdb44d3ed178349d33ff5ce --file /conda-envs/863ea15d5cdb44d3ed178349d33ff5ce/environment.yaml && \
    conda env create --prefix /conda-envs/16eb2e07c63233721fb979e7b6dd6efb --file /conda-envs/16eb2e07c63233721fb979e7b6dd6efb/environment.yaml && \
    conda env create --prefix /conda-envs/a8d69dac2431227983c93aacf938976a --file /conda-envs/a8d69dac2431227983c93aacf938976a/environment.yaml && \
    conda env create --prefix /conda-envs/076f410184348693671168900d82ff2d --file /conda-envs/076f410184348693671168900d82ff2d/environment.yaml && \
    conda env create --prefix /conda-envs/1336ed67b92af34851991cb1cb6e9ed7 --file /conda-envs/1336ed67b92af34851991cb1cb6e9ed7/environment.yaml && \
    conda env create --prefix /conda-envs/f3db69b2d9ebd3df3b2cd02edb6533d3 --file /conda-envs/f3db69b2d9ebd3df3b2cd02edb6533d3/environment.yaml && \
    conda env create --prefix /conda-envs/2c4320f38dc57a106602f72d77797147 --file /conda-envs/2c4320f38dc57a106602f72d77797147/environment.yaml && \
    conda env create --prefix /conda-envs/b7446a759507bd4367cd46bc4bf98c4a --file /conda-envs/b7446a759507bd4367cd46bc4bf98c4a/environment.yaml && \
    conda clean --all -y
