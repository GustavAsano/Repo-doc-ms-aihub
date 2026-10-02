"""Regression tests for stage completion, documentation variants and exports.

LLM calls are simulated; these tests do not require provider credentials.
"""
import base64
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import state
from app.routers import docs, export, repo
from app.src import doc_gen, doc_gen_export, mkdocs_ui


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    work = tmp_path / 'workspace'
    work.mkdir()
    monkeypatch.setattr(state, 'WORKSPACE_DIR', work)
    for module in (docs, export, repo):
        monkeypatch.setattr(module, 'WORKSPACE_DIR', work)
    monkeypatch.setattr(docs, 'OUT_DIR', tmp_path / 'out')
    monkeypatch.setattr(state, 'REPO_LIBRARY_FILE', tmp_path / 'library.json')
    monkeypatch.setattr(state, 'REPO_ASSETS_DIR', tmp_path / 'library')
    monkeypatch.setattr(state, 'FUNCTIONAL_REPO_LIBRARY_FILE', tmp_path / 'functional-library.json')
    monkeypatch.setattr(state, 'FUNCTIONAL_REPO_ASSETS_DIR', tmp_path / 'functional-library')
    code = tmp_path / 'code.json'
    code.write_text('[]')
    monkeypatch.setattr(docs, 'resolve_code_json', lambda *a, **k: code)
    return work


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(docs.router)
    app.include_router(export.router)
    app.include_router(repo.router)
    with TestClient(app) as client:
        yield client


def install_fake_generators(monkeypatch, fail_functional=False):
    def fake(variant, calls):
        def generate(source, output, language, **kwargs):
            cb = kwargs['progress_callback']
            cb({'event': 'plan', 'total_calls': 44, 'total_cost_usd': 0})
            for count in range(1, calls + 1):
                cb({'event': 'call_end', 'current_call': count, 'total_calls': 44,
                    'total_cost_usd': count * 0.1, 'cost_available': True})
            if fail_functional and variant == 'functional':
                raise RuntimeError('Functional generation failed')
            key = 'INDEX' if variant == 'technical' else 'OVERVIEW'
            Path(output).write_text(f'<!-- SECTION:{key} -->\n# {variant.title()}\n\n{variant} evidence.')
            cb({'event': 'done', 'current_call': calls, 'total_calls': 44,
                'total_cost_usd': calls * 0.1, 'cost_available': True})
        return generate
    monkeypatch.setattr(doc_gen, 'generate_doc', fake('technical', 20))
    monkeypatch.setattr(doc_gen, 'generate_functional_doc', fake('functional', 3))
    monkeypatch.setattr(doc_gen, 'generate_functional_doc_from_technical', fake('functional', 3))


def generate(client, mode):
    response = client.post('/docs/generate', json={
        'repo_name': 'example', 'language': 'PT-BR', 'generation_mode': mode,
        'documentation_sections': {'INDEX': {'title': 'Technical', 'description': 'Technical'}},
        'functional_sections': {'OVERVIEW': {'title': 'Functional', 'description': 'Functional'}},
    })
    assert response.status_code == 200
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]


@pytest.mark.parametrize('mode,technical,functional,calls,variant', [
    ('technical_only', True, False, 20, 'technical'),
    ('functional_only', False, True, 3, 'functional'),
    ('technical_and_functional', True, True, 23, 'technical'),
])
def test_generation_finishes_after_all_stages(workspace, client, monkeypatch, mode, technical, functional, calls, variant):
    install_fake_generators(monkeypatch)
    started = []
    def start(name, **kwargs):
        started.append(kwargs['doc_variant'])
        return 8001
    monkeypatch.setattr(docs, '_start_mkdocs', start)
    # Stale output from a previous run must not leak into another generation mode.
    (workspace / 'documentation.md').write_text('old technical')
    (workspace / 'functional_documentation.md').write_text('old functional')
    events = generate(client, mode)
    assert sum(ev['event'] == 'done' for ev in events) == 1
    assert events[-1]['event'] == 'done'
    result = events[-1]['result']
    assert result['docs_generated'] is technical
    assert result['functional_docs_generated'] is functional
    assert result['doc_variant'] == variant
    assert started == [variant]
    assert events[-1]['current_call'] == events[-1]['total_calls'] == calls
    assert events[-1]['total_cost_usd'] == pytest.approx(calls * 0.1)
    assert (workspace / 'documentation.md').exists() is technical
    assert (workspace / 'functional_documentation.md').exists() is functional
    assert len([ev for ev in events if ev['event'] == 'phase_done']) == int(technical) + int(functional)
    if technical and functional:
        functional_events = [ev for ev in events if ev.get('doc_variant') == 'functional' and ev['event'] == 'call_end']
        assert functional_events[0]['current_call'] == 21
        assert functional_events[-1]['current_call'] == 23
        saved = state.load_repo_library()['example::PT-BR']
        assert saved['docs_available'] and saved['functional_docs_available']


def test_functional_failure_is_not_reported_as_success(workspace, client, monkeypatch):
    install_fake_generators(monkeypatch, fail_functional=True)
    events = generate(client, 'technical_and_functional')
    assert events[-1]['event'] == 'error'
    assert 'Functional generation failed' in events[-1]['message']
    assert not any(ev['event'] == 'done' for ev in events)


def test_mkdocs_selects_functional_pages_without_index(workspace):
    folder = workspace / 'docs_functional'
    folder.mkdir()
    (folder / 'overview.md').write_text('# Functional overview\n\nBusiness flow.')
    mkdocs_ui.generate_mkdocs_config(workspace, 'example', doc_variant='functional', site_language='PT-BR')
    config = yaml.safe_load((workspace / 'mkdocs.yml').read_text())
    assert config['docs_dir'] == 'docs_functional'
    assert config['theme']['language'] == 'pt'
    assert config['nav'] == [{'Functional overview': 'overview.md'}]
    assert mkdocs_ui._resolve_docs_entry_html(folder) == 'overview.html'


def test_switching_preview_preserves_both_export_sources(workspace, client, monkeypatch):
    for variant, folder, filename in [('technical', 'docs', 'documentation.md'), ('functional', 'docs_functional', 'functional_documentation.md')]:
        (workspace / folder).mkdir()
        (workspace / folder / 'overview.md').write_text(f'# {variant} overview')
        (workspace / filename).write_text(variant)
    def start(name, **kwargs):
        mkdocs_ui.generate_mkdocs_config(workspace, name, doc_variant=kwargs['doc_variant'])
        state.set_mkdocs_port(8001)
        return 8001
    monkeypatch.setattr(docs, '_start_mkdocs', start)
    monkeypatch.setattr(state, 'is_port_open', lambda port: True)
    for variant in ['functional', 'technical']:
        response = client.post('/docs/variant', json={'repo_name': 'example', 'doc_variant': variant})
        assert response.status_code == 200
        assert response.json()['preview_url'] == '/docs/preview/overview.html'
        assert export._get_md_path('example', variant).read_text() == variant
    assert (workspace / 'documentation.md').read_text() == 'technical'
    assert (workspace / 'functional_documentation.md').read_text() == 'functional'


def test_missing_variant_does_not_fallback_to_other_document(workspace, client):
    (workspace / 'functional_documentation.md').write_text('# Functional')
    assert client.get('/export/pdf/example?doc_variant=technical').status_code == 404
    assert client.get('/export/docx/example?doc_variant=technical').status_code == 404
    assert client.post('/docs/variant', json={'repo_name': 'example', 'doc_variant': 'technical'}).status_code == 404
    assert client.get('/export/pdf/example?doc_variant=unknown').status_code == 422


@pytest.mark.parametrize('variant,cover', [('technical', 'Documentação Técnica'), ('functional', 'Documentação Funcional')])
def test_word_cover_and_content_match_requested_variant(workspace, client, variant, cover):
    (workspace / 'documentation.md').write_text('# Technical\n\nTECHNICAL CONTENT')
    (workspace / 'functional_documentation.md').write_text('# Functional\n\nFUNCTIONAL CONTENT')
    response = client.get(f'/export/docx/example?doc_variant={variant}&language=PT-BR')
    assert response.status_code == 200
    data = base64.b64decode(response.json()['data'])
    with ZipFile(BytesIO(data)) as archive:
        text = archive.read('word/document.xml').decode()
    assert cover in text
    assert f'{variant.upper()} CONTENT' in text
    assert f'{("functional" if variant == "technical" else "technical").upper()} CONTENT' not in text


@pytest.mark.parametrize('variant', ['technical', 'functional'])
def test_pdf_passes_matching_content_and_cover_kind(workspace, client, monkeypatch, variant):
    (workspace / 'documentation.md').write_text('technical')
    (workspace / 'functional_documentation.md').write_text('functional')
    received = {}
    def build(**kwargs):
        received.update(kwargs)
        return b'%PDF-test'
    monkeypatch.setattr(doc_gen_export, 'build_pdf_bytes', build)
    response = client.get(f'/export/pdf/example?doc_variant={variant}&language=PT-BR')
    assert response.status_code == 200
    assert received['doc_kind'] == received['md_text'] == variant
    expected = 'Documentação Funcional' if variant == 'functional' else 'Documentação Técnica'
    assert doc_gen_export._pdf_i18n('PT-BR', 'example', 'today', doc_kind=variant)['doc_subtitle'] == expected


def test_library_restore_preserves_canonical_variant_files(workspace, tmp_path):
    tech = tmp_path / 'saved-tech'
    func = tmp_path / 'saved-func'
    tech.mkdir()
    func.mkdir()
    (tech / 'index.md').write_text('# Technical')
    (func / 'overview.md').write_text('# Functional')
    tech_md = tmp_path / 'technical.md'
    func_md = tmp_path / 'functional.md'
    tech_md.write_text('technical')
    func_md.write_text('functional')
    entry = {'library_docs_dir': str(tech), 'library_documentation_md': str(tech_md),
             'library_functional_docs_dir': str(func), 'library_functional_documentation_md': str(func_md)}
    assert state.activate_repo_assets(entry, doc_variant='functional')
    assert (workspace / 'documentation.md').read_text() == 'technical'
    assert (workspace / 'functional_documentation.md').read_text() == 'functional'
    # Switching to a functional-only saved entry must clear old technical files.
    entry.pop('library_documentation_md')
    entry['library_docs_dir'] = str(func)
    assert state.activate_repo_assets(entry, doc_variant='functional')
    assert not (workspace / 'documentation.md').exists()
    assert not (workspace / 'docs').exists()


def test_functional_library_activation_uses_saved_functional_entry(workspace, client, monkeypatch):
    install_fake_generators(monkeypatch)
    monkeypatch.setattr(docs, '_start_mkdocs', lambda *a, **k: 8001)
    # Loading a repository creates a technical library entry before any generation.
    state.upsert_library_entry('example', {'docs_available': False, 'functional_docs_available': False}, 'PT-BR')
    generate(client, 'functional_only')
    state.reset_workspace()
    response = client.post('/repo/activate', data={
        'entry_key': 'example::PT-BR', 'doc_variant': 'functional', 'start_mkdocs': 'false',
    })
    assert response.status_code == 200
    result = response.json()
    assert result['doc_variant'] == 'functional'
    assert result['functional_docs_generated'] is True
    assert result['docs_generated'] is False
    assert result['generation_mode'] == 'functional_only'
    assert (workspace / 'functional_documentation.md').exists()
    assert not (workspace / 'documentation.md').exists()


@pytest.mark.parametrize('variant,cover', [('technical', 'Documentação Técnica'), ('functional', 'Documentação Funcional')])
def test_real_pdf_cover_and_content(workspace, client, variant, cover):
    import re
    import zlib

    (workspace / 'documentation.md').write_text('# Technical\n\nTECHNICAL CONTENT')
    (workspace / 'functional_documentation.md').write_text('# Functional\n\nFUNCTIONAL CONTENT')
    response = client.get(f'/export/pdf/example?doc_variant={variant}&language=PT-BR')
    assert response.status_code == 200
    pdf = base64.b64decode(response.json()['data'])
    assert pdf.startswith(b'%PDF-')
    # fpdf2 uses Helvetica with Latin-1 text and compressed page streams.
    streams = re.findall(rb'stream\r?\n(.*?)\r?\nendstream', pdf, re.S)
    contents = b'\n'.join(zlib.decompress(stream) for stream in streams).decode('latin-1')
    assert cover in contents
    assert f'{variant.upper()} CONTENT' in contents
    assert f'{("functional" if variant == "technical" else "technical").upper()} CONTENT' not in contents


def test_mkdocs_builds_selected_variant_html(workspace):
    import subprocess
    import sys

    (workspace / 'docs').mkdir()
    (workspace / 'docs' / 'index.md').write_text('# Technical\n\nTECHNICAL SITE CONTENT')
    (workspace / 'docs_functional').mkdir()
    (workspace / 'docs_functional' / 'overview.md').write_text('# Functional\n\nFUNCTIONAL SITE CONTENT')
    for variant, page in [('technical', 'index.html'), ('functional', 'overview.html')]:
        mkdocs_ui.generate_mkdocs_config(workspace, 'example', doc_variant=variant)
        build = subprocess.run([sys.executable, '-m', 'mkdocs', 'build', '--quiet'],
                               cwd=workspace, capture_output=True, text=True)
        assert build.returncode == 0, build.stderr
        html = (workspace / 'site' / page).read_text()
        assert f'{variant.upper()} SITE CONTENT' in html
        other = 'FUNCTIONAL' if variant == 'technical' else 'TECHNICAL'
        assert f'{other} SITE CONTENT' not in html


@pytest.mark.parametrize('mode,kind,technical,functional', [
    ('technical_only', 'technical', True, False),
    ('functional_only', 'functional', False, True),
    ('technical_and_functional', 'technical', True, True),
])
def test_library_tags_match_generated_documentation(workspace, client, monkeypatch, mode, kind, technical, functional):
    install_fake_generators(monkeypatch)
    monkeypatch.setattr(docs, '_start_mkdocs', lambda *a, **k: 8001)
    state.upsert_library_entry('example', {'docs_available': False, 'functional_docs_available': False}, 'PT-BR')
    assert client.get('/repo/library?kind=technical').json()['entries'] == []
    generate(client, mode)
    entries = client.get(f'/repo/library?kind={kind}').json()['entries']
    assert len(entries) == 1
    assert entries[0]['docs_available'] is technical
    assert entries[0]['functional_docs_available'] is functional


def test_snapshot_handles_code_and_graph_already_in_library(workspace, tmp_path):
    saved = state._library_repo_dir_for_language('example', 'PT-BR')
    saved.mkdir(parents=True)
    code = saved / 'code.json'
    graph = saved / 'graph.json'
    code.write_text('[]')
    graph.write_text('{"nodes": [], "edges": []}')
    (workspace / 'docs').mkdir()
    (workspace / 'docs' / 'index.md').write_text('# Technical')
    (workspace / 'documentation.md').write_text('technical')
    (workspace / 'docs_functional').mkdir()
    (workspace / 'docs_functional' / 'overview.md').write_text('# Functional')
    (workspace / 'functional_documentation.md').write_text('functional')
    snapshot = state.snapshot_repo_assets('example', code, 'PT-BR', str(graph), include_functional=True)
    assert snapshot['docs_available'] is True
    assert snapshot['functional_docs_available'] is True
    assert (saved / 'documentation.md').read_text() == 'technical'
    assert (saved / 'functional_documentation.md').read_text() == 'functional'
    assert snapshot['library_graph_json'] == str(graph)


def test_mkdocs_waits_for_slow_startup(workspace, monkeypatch):
    import socket
    import subprocess
    import sys
    import time
    import httpx

    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    real_popen = subprocess.Popen
    def delayed_server(args, **kwargs):
        script = ('import time; time.sleep(1.8); '
                  'from http.server import HTTPServer, SimpleHTTPRequestHandler; '
                  f'HTTPServer(("127.0.0.1", {port}), SimpleHTTPRequestHandler).serve_forever()')
        return real_popen([sys.executable, '-c', script], **kwargs)
    monkeypatch.setattr(mkdocs_ui.subprocess, 'Popen', delayed_server)
    start = time.monotonic()
    try:
        ready_port, error = mkdocs_ui.serve_mkdocs(workspace, port=port, force_restart=True, startup_timeout=10)
        assert error is None
        assert ready_port == port
        assert time.monotonic() - start >= 1.8
        assert httpx.get(f'http://127.0.0.1:{port}/').status_code == 200
    finally:
        mkdocs_ui._stop_mkdocs_process()


def test_variant_switch_waits_for_real_mkdocs(workspace, client, monkeypatch):
    import socket

    def free_port():
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            return sock.getsockname()[1]
    monkeypatch.setattr(mkdocs_ui, 'find_free_port', free_port)
    for folder, page, content in [('docs', 'index.md', 'TECHNICAL SITE'),
                                   ('docs_functional', 'overview.md', 'FUNCTIONAL SITE')]:
        (workspace / folder).mkdir()
        (workspace / folder / page).write_text(f'# Overview\n\n{content}')
    try:
        for variant in ['functional', 'technical', 'functional']:
            response = client.post('/docs/variant', json={'repo_name': 'example', 'doc_variant': variant})
            assert response.status_code == 200, response.text
            html = client.get(response.json()['preview_url'])
            assert html.status_code == 200
            assert f'{variant.upper()} SITE' in html.text
    finally:
        mkdocs_ui._stop_mkdocs_process()
        state.set_mkdocs_port(None)
