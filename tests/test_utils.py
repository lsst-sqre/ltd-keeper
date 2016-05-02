import pytest
from app.exceptions import ValidationError
from app.utils import (auto_slugify_edition, validate_path_slug,
                       validate_product_slug)


@pytest.mark.parametrize(
    'git_refs,expected',
    [(['tickets/DM-1234'], 'DM-1234'),
     (['master'], 'master'),
     (['tickets/DM-1234', 'tickets/DM-5678'],
      'tickets-DM-1234-tickets-DM-5678')])
def test_auto_slugify_edition(git_refs, expected):
    assert expected == auto_slugify_edition(git_refs)
    assert validate_path_slug(auto_slugify_edition(git_refs))


def test_validate_product_slug():
    with pytest.raises(ValidationError):
        validate_product_slug('DM-1234')
    with pytest.raises(ValidationError):
        validate_product_slug('DM_1234')
    assert validate_product_slug('dm-1234') is True
