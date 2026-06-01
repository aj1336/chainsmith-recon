from unittest.mock import MagicMock


def _make_city_response(
    country="United States",
    iso_code="US",
    region="Virginia",
    city="Ashburn",
    lat=39.0438,
    lon=-77.4874,
):
    """Build a mock geoip2 city response."""
    resp = MagicMock()
    resp.country.name = country
    resp.country.iso_code = iso_code
    resp.subdivisions.most_specific.name = region
    resp.subdivisions.__bool__ = lambda self: True
    resp.city.name = city
    resp.location.latitude = lat
    resp.location.longitude = lon
    return resp


def _make_asn_response(asn_number, org_name):
    """Build a mock geoip2 ASN response."""
    resp = MagicMock()
    resp.autonomous_system_number = asn_number
    resp.autonomous_system_organization = org_name
    return resp


def _setup_readers(mock_reader_cls, city_resp, asn_resp, city_available=True, asn_available=True):
    """Wire a patched geoip2.database.Reader to return pre-built city/asn readers.

    Returns (city_reader, asn_reader) so tests can make per-IP assertions on
    the reader objects if needed.
    """
    city_reader = MagicMock()
    asn_reader = MagicMock()

    if city_resp is not None:
        city_reader.city.return_value = city_resp
    if asn_resp is not None:
        asn_reader.asn.return_value = asn_resp

    if city_available and asn_available:
        mock_reader_cls.side_effect = [city_reader, asn_reader]
    elif asn_available:
        mock_reader_cls.return_value = asn_reader
    elif city_available:
        mock_reader_cls.return_value = city_reader

    return city_reader, asn_reader


def _find_db_stub(filename):
    """Stub for _find_db_file that returns a fake path for any filename."""
    return f"/fake/{filename}"


def _find_db_asn_only(filename):
    """Stub for _find_db_file that only finds the ASN database."""
    return f"/fake/{filename}" if "ASN" in filename else None


class TestGeoIpRegistration:
    """Verify GeoIP check is properly registered."""

    def test_geoip_in_resolver(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "geoip" in names
