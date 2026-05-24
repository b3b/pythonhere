FROM quay.io/jupyter/base-notebook:python-3.13

COPY --chown=${NB_USER}:users . /home/${NB_USER}/src
COPY --chown=${NB_USER}:users examples /home/${NB_USER}/examples

RUN cd /home/${NB_USER}/src && \
    python -m pip install --upgrade pip && \
    python -m pip install . --group docker && \
    python -m pip check && \
    jupyter labextension disable --level=sys_prefix "@jupyterlab/apputils-extension:announcements" && \
    mkdir -p /opt/conda/share/jupyter/lab/settings && \
    cat > /opt/conda/share/jupyter/lab/settings/overrides.json <<'EOF'
{
  "@jupyterlab/notebook-extension:tracker": {
    "codeCellConfig": {
      "lineNumbers": true
    }
  },
  "@jupyterlab/fileeditor-extension:plugin": {
    "editorConfig": {
      "lineNumbers": true
    }
  },
  "@jupyterlab/console-extension:tracker": {
    "promptCellConfig": {
      "lineNumbers": true
    }
  }
}
EOF

RUN cd /home/${NB_USER}/examples && \
    jupytext --to ipynb *.md && \
    rm *.md && \
    rm -rf /home/${NB_USER}/.cache && \
    rm -rf /home/${NB_USER}/src
