"""
Tests for ilmX-specific customisations of the Image Explorer XBlock.

The ilmX changes are presentation-only (CSS + the JS that applies the hotspot
sprite), so these tests check the rendered fragment and the shipped assets.
"""
import re
import unittest
from importlib import resources
from unittest.mock import Mock, patch

from xblock.field_data import DictFieldData

from image_explorer.image_explorer import ImageExplorerBlock

from .utils import MockRuntime, patch_static_replace_module


def _asset(path):
    return resources.files('image_explorer').joinpath(path).read_text(encoding='utf-8')


class TestIlmxImageExplorerCustomizations(unittest.TestCase):
    """ilmX customisation tests."""

    def setUp(self):
        super().setUp()
        patch_static_replace_module()
        runtime = MockRuntime()
        runtime._services['replace_urls'] = Mock(  # pylint: disable=protected-access
            replace_urls=lambda html, static_replace_only=False: re.sub(
                r'/static/([^"\s]*)', r'/course/test-course/assets/\1', html
            )
        )
        runtime.local_resource_url = lambda block, uri: '/xblock/resource/image-explorer/' + uri
        self.block = ImageExplorerBlock(runtime, DictFieldData({}), None)
        self.block.course_id = 'abc/xyz/123'
        patcher = patch.object(ImageExplorerBlock, '_get_unique_id', return_value='uid')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_block_type_and_fields_unchanged(self):
        """Course content from Juniper relies on these names."""
        from importlib.metadata import entry_points  # pylint: disable=import-outside-toplevel
        eps = {ep.name: ep.value for ep in entry_points(group='xblock.v1')}
        self.assertEqual(eps.get('image-explorer'), 'image_explorer:ImageExplorerBlock')
        for name in ('display_name', 'data', '_hotspot_coordinates_centered', 'opened_hotspots'):
            self.assertIn(name, ImageExplorerBlock.fields)

    def test_student_view_css_contains_ilmx_overrides(self):
        frag = self.block.student_view({})
        css = '\n'.join(r.data for r in frag.resources if r.kind == 'text' and r.mimetype == 'text/css')
        # Close button stays flat on hover/active
        self.assertIn('.image-explorer-close-reveal:hover', css)
        self.assertIn('background-image: none !important', css)
        # Mobile: hotspots no longer shrunk to 16px
        mobile = css.split('@media only screen and (max-width: 767px)')[1].split('/*Studio*/')[0]
        self.assertNotIn('width: 16px', mobile)
        self.assertNotIn('margin-left: -8px', mobile)

    def test_hotspot_sprite_applied_with_important_priority(self):
        js = _asset('public/js/image_explorer.js')
        self.assertIn('setProperty("background-image"', js)
        self.assertIn('"important"', js)
        # No hard-coded collected-static path (the Juniper fork used a hashed studio URL)
        css = _asset('public/css/image_explorer.css')
        self.assertNotIn('/static/studio/xblock/resources', css)

    def test_student_view_passes_sprite_url_to_js(self):
        frag = self.block.student_view({})
        self.assertIn('hotspot-sprite.png', frag.json_init_args['hotspot_image'])
