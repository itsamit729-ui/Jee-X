from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.services.frontend_delivery import frontend_response


def test_public_deep_links_serve_their_own_html_while_accounts_get_a_private_shell(tmp_path):
    (tmp_path/'index.html').write_text('<h1>Jee Edge public home</h1>')
    (tmp_path/'spa.html').write_text('<meta name="robots" content="noindex, follow"><div id="root"></div>')
    public=tmp_path/'mhtcet-mock-tests';public.mkdir()
    (public/'index.html').write_text('<link rel="canonical" href="https://jeeedge.in/mhtcet-mock-tests"><h1>MHT-CET mocks</h1>')
    assets=tmp_path/'assets';assets.mkdir();(assets/'app-hash.js').write_text('app')
    app=FastAPI()
    @app.get('/{path:path}')
    def serve(path:str):return frontend_response(tmp_path,path)
    client=TestClient(app)
    assert 'public home' in client.get('/').text
    response=client.get('/mhtcet-mock-tests')
    assert 'MHT-CET mocks' in response.text and response.headers['cache-control']=='no-cache'
    assert client.get('/mhtcet-mock-tests/').text==response.text
    for path in ('/login','/teacher/profile','/dashboard','/pyq?exam=jee_main','/u/student.alias','/u/student.png'):
        private=client.get(path)
        assert private.status_code==200
        assert private.headers['x-robots-tag']=='noindex, follow'
        assert 'noindex, follow' in private.text and 'public home' not in private.text
    for path in ('/assets/missing.js','/question-images/missing','/missing.xml','/api/missing'):
        assert client.get(path).status_code==404
    assert 'immutable' in client.get('/assets/app-hash.js').headers['cache-control']
