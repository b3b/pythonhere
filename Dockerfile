FROM jupyter/base-notebook:python-3.8.6

COPY . /src
COPY examples /home/${NB_USER}/examples

RUN cd /src && pip install .[dev,docker]

USER root
RUN cd /home/${NB_USER}/examples && \
    jupytext --to ipynb *.md && \
    rm *.md && \
    chown -R ${NB_USER} \
    /usr/local/bin/fix-permissions /home/${NB_USER}/examples &&\
    rm -rf /home/${NB_USER}/.cache && \
    rm -rf /src
