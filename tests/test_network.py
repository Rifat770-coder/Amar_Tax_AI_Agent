from amar_tax.network import NoRedirect


def test_authorization_is_not_forwarded_on_redirect():
    assert NoRedirect().redirect_request(None,None,302,"redirect",{},"https://different.example") is None
