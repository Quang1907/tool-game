"""Unit tests for Computer Vision, Template Matching, Screen Capture, and Recognition Validation."""

from pathlib import Path
import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.core.card import Card, Rank, Suit
from app.vision.card_detector import CardCrop, CardDetector
from app.vision.card_recognizer import CardRecognizer, DetectedCard
from app.vision.card_reference_library import CardReferenceLibrary
from app.vision.image_preprocessor import ImagePreprocessor
from app.vision.recognition_validator import RecognitionValidator
from app.vision.screen_capture import ScreenCapture
from app.vision.template_engine import CardTemplateEngine


class TestImagePreprocessor:
    def test_to_gray_and_rectify(self):
        # 3-channel synthetic image (200x200 BGR)
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        img[50:150, 50:150] = (255, 255, 255)  # White box

        gray = ImagePreprocessor.to_gray(img)
        assert len(gray.shape) == 2
        assert gray.shape == (200, 200)

        rectified = ImagePreprocessor.rectify_card(img[50:150, 50:150])
        assert rectified.shape == (
            ImagePreprocessor.CARD_TARGET_HEIGHT,
            ImagePreprocessor.CARD_TARGET_WIDTH,
            3,
        )


class TestCardTemplateEngine:
    def test_rank_and_suit_template_generation(self):
        engine = CardTemplateEngine()
        assert len(engine._rank_templates) == 13
        assert len(engine._suit_templates) == 4

        # Render synthetic 'A' glyph and test matching
        img_a = Image.new("L", (30, 40), 255)  # White bg
        draw = ImageDraw.Draw(img_a)
        draw.text((5, 5), "A", fill=0)          # Black text
        patch_a = np.array(img_a, dtype=np.uint8)

        rank_match, conf = engine.match_rank(patch_a)
        assert rank_match == Rank.ACE
        assert conf > 0.60

    def test_suit_color_discrimination(self):
        engine = CardTemplateEngine()
        # Test Red suit matching with diamond geometry
        diamond_patch = np.zeros((30, 30), dtype=np.uint8)
        pts = np.array([[15, 3], [27, 15], [15, 27], [3, 15]], dtype=np.int32)
        import cv2
        cv2.fillConvexPoly(diamond_patch, pts, 255)

        suit_match, conf = engine.match_suit(diamond_patch, is_red=True)
        assert suit_match in (Suit.DIAMONDS, Suit.HEARTS)
        assert conf > 0.50


class TestCardDetector:
    def test_detect_single_card_random_position(self):
        """CardDetector discovers an upright card placed at an arbitrary position without fixed grids."""
        # Dark green poker table
        table = np.zeros((300, 400, 3), dtype=np.uint8)
        table[:, :] = (20, 80, 20)

        # Place white card at arbitrary position (60, 45) with size 80x112 (aspect ~0.71)
        cx, cy, cw, ch = 60, 45, 80, 112
        table[cy : cy + ch, cx : cx + cw] = (245, 245, 245)
        # Rank glyph mark in top-left
        table[cy + 4 : cy + 24, cx + 4 : cx + 20] = (20, 20, 20)

        detector = CardDetector()
        crops, debug = detector.detect_card_objects(table)

        assert len(crops) == 1
        assert debug.total_detected == 1
        det = crops[0].detection
        assert det is not None
        assert abs(det.bbox[0] - cx) <= 5
        assert abs(det.bbox[1] - cy) <= 5
        assert abs(det.bbox[2] - cw) <= 5
        assert abs(det.bbox[3] - ch) <= 5
        assert det.detection_confidence >= 0.85
        assert crops[0].image.shape == (
            ImagePreprocessor.CARD_TARGET_HEIGHT,
            ImagePreprocessor.CARD_TARGET_WIDTH,
            3,
        )

    def test_detect_multiple_scattered_cards(self):
        """CardDetector discovers multiple cards scattered at unaligned, random positions."""
        table = np.zeros((400, 600, 3), dtype=np.uint8)
        table[:, :] = (30, 70, 30)

        # 3 scattered cards
        positions = [(40, 50, 70, 98), (220, 180, 70, 98), (440, 80, 70, 98)]
        for x, y, w, h in positions:
            table[y : y + h, x : x + w] = (240, 240, 240)
            table[y + 4 : y + 20, x + 4 : x + 16] = (10, 10, 10)

        detector = CardDetector()
        crops = detector.detect_cards(table)

        assert len(crops) == 3
        # Ensure detected coordinates correspond to actual scattered positions
        detected_xs = sorted([c.bbox[0] for c in crops])
        assert abs(detected_xs[0] - 40) <= 6
        assert abs(detected_xs[1] - 220) <= 6
        assert abs(detected_xs[2] - 440) <= 6

    def test_reject_non_card_ui_elements(self):
        """CardDetector rejects saturated game buttons and dark empty slots."""
        table = np.zeros((300, 500, 3), dtype=np.uint8)
        table[:, :] = (25, 75, 25)

        # Real card
        table[40:152, 40:120] = (245, 245, 245)
        table[45:65, 45:60] = (10, 10, 10)

        # Orange UI Button ("Xếp xong" - highly saturated orange, low whiteness)
        table[40:90, 200:320] = (0, 140, 255)  # BGR orange: High Saturation

        # Dark empty slot outline
        table[40:152, 360:440] = (35, 45, 35)

        detector = CardDetector()
        crops, debug = detector.detect_card_objects(table)

        assert len(crops) == 1
        assert crops[0].bbox[0] < 150  # Only the real card is detected!
        assert debug.total_rejected >= 1
        assert "ui_button" in debug.rejection_breakdown

    def test_dissect_overlapping_cards(self):
        """CardDetector dissects cascaded overlapping cards using vertical edge transitions."""
        table = np.zeros((200, 400, 3), dtype=np.uint8)
        table[:, :] = (20, 70, 20)

        # Cascaded cluster of 3 cards overlapping horizontally:
        # Card 1: x=50, Card 2: x=90, Card 3: x=130 (width=70, height=100)
        h, w = 100, 70
        y = 40
        # Draw base
        table[y : y + h, 50 : 50 + w] = (235, 235, 235)
        table[y + 4 : y + 20, 54 : 68] = (10, 10, 10)

        # Overlapping card 2
        table[y : y + h, 90 : 90 + w] = (245, 245, 245)
        table[y : y + h, 90 : 92] = (150, 150, 150)  # Edge shadow
        table[y + 4 : y + 20, 94 : 108] = (10, 10, 10)

        # Overlapping card 3
        table[y : y + h, 130 : 130 + w] = (250, 250, 250)
        table[y : y + h, 130 : 132] = (150, 150, 150)  # Edge shadow
        table[y + 4 : y + 20, 134 : 148] = (10, 10, 10)

        detector = CardDetector()
        crops, _ = detector.detect_card_objects(table)

        assert len(crops) >= 2
        for crop in crops:
            assert crop.detection.is_overlapping is True


class TestScreenCaptureMultiMonitor:
    def test_screen_enumeration_and_crop(self):
        screens = ScreenCapture.get_available_screens()
        assert len(screens) >= 1
        assert screens[0].index == 1

        # Test safe cropping within bounds
        dummy_img = np.zeros((500, 800, 3), dtype=np.uint8)
        crop = ScreenCapture.crop_region(dummy_img, (50, 50, 200, 150))
        assert crop.shape == (150, 200, 3)

        # Test out of bounds clamping
        crop_clamped = ScreenCapture.crop_region(dummy_img, (-20, -30, 200, 150))
        assert crop_clamped.shape[0] <= 150
        assert crop_clamped.shape[1] <= 200


class TestCardRecognizer:
    def test_recognizer_template_matching(self):
        recognizer = CardRecognizer()
        assert recognizer.has_trained_model is False

        # Create a synthetic card patch: White card with black top-left 'A'
        card_img = np.ones((ImagePreprocessor.CARD_TARGET_HEIGHT, ImagePreprocessor.CARD_TARGET_WIDTH, 3), dtype=np.uint8) * 255
        corner_h = int(ImagePreprocessor.CARD_TARGET_HEIGHT * 0.50)
        corner_w = int(ImagePreprocessor.CARD_TARGET_WIDTH * 0.42)
        corner = card_img[0:corner_h, 0:corner_w].copy()

        # Draw black 'A' in rank area
        pil_corner = Image.fromarray(corner)
        draw = ImageDraw.Draw(pil_corner)
        draw.text((4, 2), "A", fill=(0, 0, 0))
        corner_with_glyph = np.array(pil_corner)

        crop = CardCrop(
            bbox=(0, 0, 120, 168),
            image=card_img,
            corner_crop=corner_with_glyph,
        )

        detected = recognizer.recognize_crop(crop)
        assert detected.card is not None
        assert detected.card.rank == Rank.ACE
        assert detected.confidence > 0.40


class TestRecognitionValidator:
    def test_validation_success_with_13_unique_cards(self):
        detected_cards = [
            DetectedCard(
                card=Card.from_id(i),
                confidence=0.95,
                bbox=(i * 10, 0, 100, 140),
                raw_crop=np.zeros((140, 100, 3), dtype=np.uint8),
            )
            for i in range(13)
        ]

        report = RecognitionValidator.validate(detected_cards)
        assert report.is_valid is True
        assert report.card_count == 13
        assert len(report.duplicates) == 0
        assert report.unrecognized_count == 0

    def test_validation_failure_on_duplicate(self):
        detected_cards = [
            DetectedCard(
                card=Card.from_id(i % 12),  # Card 0 will appear twice!
                confidence=0.95,
                bbox=(i * 10, 0, 100, 140),
                raw_crop=np.zeros((140, 100, 3), dtype=np.uint8),
            )
            for i in range(13)
        ]

        report = RecognitionValidator.validate(detected_cards)
        assert report.is_valid is False
        assert len(report.duplicates) > 0
        assert "trùng" in report.message

    def test_validation_failure_on_missing_cards(self):
        detected_cards = [
            DetectedCard(
                card=Card.from_id(i),
                confidence=0.95,
                bbox=(i * 10, 0, 100, 140),
                raw_crop=np.zeros((140, 100, 3), dtype=np.uint8),
            )
            for i in range(11)  # Only 11 cards
        ]

        report = RecognitionValidator.validate(detected_cards)
        assert report.is_valid is False
        assert report.card_count == 11
        assert report.missing_count == 2
        assert "13 lá" in report.message


class TestCardReferenceLibrary:
    """Unit tests for CardReferenceLibrary persistence, deduplication, matching, and recognizer fusion."""

    @pytest.fixture
    def test_lib(self, tmp_path):
        from app.database.db import DatabaseManager
        from app.vision.card_reference_library import CardReferenceLibrary
        db = DatabaseManager(db_path=tmp_path / "test.db")
        return CardReferenceLibrary(db_manager=db, storage_dir=tmp_path / "refs")

    def _create_synthetic_card_image(self, rank_str: str, is_red: bool) -> np.ndarray:
        """Helper to create a recognizable synthetic card crop (120x168 BGR)."""
        img = np.full((168, 120, 3), 245, dtype=np.uint8)  # Off-white card surface
        color = (20, 20, 210) if is_red else (20, 20, 20)   # Red or Black in BGR

        # Draw border
        import cv2
        cv2.rectangle(img, (2, 2), (117, 165), (180, 180, 180), 1)

        # Draw rank character on corner
        cv2.putText(img, rank_str, (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        # Draw suit symbol representation
        cv2.circle(img, (22, 55), 8, color, -1)
        return img

    def test_reference_library_add_and_deduplicate(self, test_lib, tmp_path):
        card = Card(Rank.ACE, Suit.SPADES)
        img = self._create_synthetic_card_image("A", is_red=False)

        # 1. Add reference
        ref1 = test_lib.add_reference(image=img, card=card, source="user_confirmed")
        assert ref1.card_code == "AS"
        assert ref1.confirmed is True
        assert Path(ref1.image_path).exists()

        # 2. Add identical image -> Deduplication check
        ref2 = test_lib.add_reference(image=img, card=card, source="user_confirmed")
        assert ref2.id == ref1.id  # Same ID returned, deduplicated!

        refs = test_lib.get_references_for_card("AS")
        assert len(refs) == 1

    def test_reference_library_multiple_samples_for_same_card(self, test_lib):
        card = Card(Rank.KING, Suit.HEARTS)
        img1 = self._create_synthetic_card_image("K", is_red=True)
        img2 = np.copy(img1)
        # Modify img2 slightly so it has a different hash
        img2[100:120, 50:70] = (0, 0, 180)

        ref1 = test_lib.add_reference(image=img1, card=card)
        ref2 = test_lib.add_reference(image=img2, card=card)

        assert ref1.id != ref2.id
        refs = test_lib.get_references_for_card("KH")
        assert len(refs) == 2

        summary = test_lib.get_summary()
        assert summary["counts"]["KH"] == 2
        assert summary["total_samples"] >= 2

    def test_reference_library_matching_and_alternatives(self, test_lib):
        card_10d = Card(Rank.TEN, Suit.DIAMONDS)
        img_10d = self._create_synthetic_card_image("10", is_red=True)
        test_lib.add_reference(image=img_10d, card=card_10d)

        # Query with exact image
        match = test_lib.match_crop(img_10d)
        assert match is not None
        assert match.card_code == "10D"
        assert match.card == card_10d
        assert match.score >= 0.85
        assert match.is_confident is True

        # Query with empty image
        assert test_lib.match_crop(np.zeros((5, 5, 3), dtype=np.uint8)) is None

    def test_reference_library_deletion(self, test_lib):
        card = Card(Rank.QUEEN, Suit.CLUBS)
        img = self._create_synthetic_card_image("Q", is_red=False)
        ref = test_lib.add_reference(image=img, card=card)

        path = Path(ref.image_path)
        assert path.exists()

        # Delete single reference
        deleted = test_lib.delete_reference(ref.id)
        assert deleted is True
        assert not path.exists()
        assert len(test_lib.get_references_for_card("QC")) == 0

    def test_reference_library_persistence_across_reloads(self, tmp_path):
        from app.database.db import DatabaseManager
        from app.vision.card_reference_library import CardReferenceLibrary

        db_path = tmp_path / "persistent.db"
        storage_path = tmp_path / "persistent_refs"

        # Instance 1: add reference
        db1 = DatabaseManager(db_path=db_path)
        lib1 = CardReferenceLibrary(db_manager=db1, storage_dir=storage_path)
        card = Card(Rank.JACK, Suit.SPADES)
        img = self._create_synthetic_card_image("J", is_red=False)
        lib1.add_reference(image=img, card=card)

        # Instance 2: reload from same DB and storage
        db2 = DatabaseManager(db_path=db_path)
        lib2 = CardReferenceLibrary(db_manager=db2, storage_dir=storage_path)

        match = lib2.match_crop(img)
        assert match is not None
        assert match.card_code == "JS"
        assert match.card == card
        assert match.score >= 0.85

    def test_card_recognizer_fusion_with_reference_library(self, test_lib):
        card_as = Card(Rank.ACE, Suit.SPADES)
        img_as = self._create_synthetic_card_image("A", is_red=False)
        test_lib.add_reference(image=img_as, card=card_as)

        recognizer = CardRecognizer(reference_library=test_lib)

        # Build CardCrop
        crop = CardCrop(
            bbox=(0, 0, 120, 168),
            image=img_as,
            corner_crop=img_as[0:70, 0:50],
        )

        det = recognizer.recognize_crop(crop)
        assert det.card == card_as
        assert det.card_code == "AS"
        assert det.is_reference_match is True
        assert det.confidence >= 0.85
        assert det.is_uncertain is False

    def test_detected_card_to_dict_format(self):
        card = Card(Rank.KING, Suit.HEARTS)
        det = DetectedCard(
            card=card,
            confidence=0.96,
            bbox=(10, 20, 80, 120),
            raw_crop=np.zeros((120, 80, 3), dtype=np.uint8),
            rank_confidence=0.98,
            suit_confidence=0.94,
            overall_confidence=0.96,
            is_verified=True,
            is_reference_match=True,
            is_uncertain=False,
            alternative_candidates=[("KH", 0.96), ("KD", 0.65)],
        )
        d = det.to_dict()
        assert d["card_code"] == "KH"
        assert d["rank"] == "K"
        assert d["suit"] == "H"
        assert d["rank_confidence"] == 0.98
        assert d["suit_confidence"] == 0.94
        assert d["overall_confidence"] == 0.96
        assert d["confidence"] == 0.96
        assert d["is_verified"] is True
        assert d["is_reference_match"] is True
        assert d["is_uncertain"] is False
        assert len(d["alternative_candidates"]) == 2


class TestRealCardRecognition:
    """Rigorous tests executed on actual in-game card screenshots from tests/fixtures/real_samples/."""

    FIXTURE_DIR = Path(__file__).parent / "fixtures" / "real_samples"

    @pytest.fixture
    def test_lib(self, tmp_path):
        from app.database.db import DatabaseManager
        from app.vision.card_reference_library import CardReferenceLibrary
        db = DatabaseManager(db_path=tmp_path / "real_test.db")
        return CardReferenceLibrary(db_manager=db, storage_dir=tmp_path / "real_refs")

    def _load_fixture(self, prefix: str) -> np.ndarray:
        files = list(self.FIXTURE_DIR.glob(f"{prefix}*.png"))
        assert len(files) > 0, f"Missing fixture starting with {prefix}"
        img = cv2.imread(str(files[0]))
        assert img is not None and img.size > 0
        return img

    def test_real_fixtures_exist(self):
        fixtures = list(self.FIXTURE_DIR.glob("*.png"))
        assert len(fixtures) >= 8, f"Expected at least 8 real sample images, found {len(fixtures)}"

    def test_rank_and_suit_isolated_crops(self):
        """CardDetector generates isolated rank_crop and suit_crop without middle illustrations."""
        detector = CardDetector()
        img_jc = self._load_fixture("JC")

        crops = detector._build_card_crops(img_jc, [(0, 0, 120, 168)])
        assert len(crops) == 1
        crop = crops[0]

        assert crop.rank_crop is not None
        assert crop.suit_crop is not None
        assert crop.rank_crop.shape == (40, 36, 3)
        assert crop.suit_crop.shape == (36, 36, 3)

    def test_extract_primary_glyph_clean_and_noise_free(self):
        """extract_primary_glyph cleans green selection glow and extracts primary character."""
        for code in ["4H", "5D", "6D", "7D", "JC", "JH", "KC", "KD"]:
            img = self._load_fixture(code)
            r_crop = img[8:48, 8:44]
            s_crop = img[46:82, 8:44]

            r_glyph = CardReferenceLibrary.extract_primary_glyph(r_crop, (24, 36))
            s_glyph = CardReferenceLibrary.extract_primary_glyph(s_crop, (28, 28))

            assert r_glyph.shape == (36, 24)
            assert s_glyph.shape == (28, 28)
            assert cv2.countNonZero(r_glyph) >= 20, f"Rank glyph for {code} is empty"
            assert cv2.countNonZero(s_glyph) >= 20, f"Suit glyph for {code} is empty"

    def test_cross_learning_suit_c_from_jc_to_kc(self, test_lib):
        """Confirming JC provides suit glyph ♣, allowing instant identification of KC suit."""
        img_jc = self._load_fixture("JC")
        img_kc = self._load_fixture("KC")

        card_jc = Card(Rank.JACK, Suit.CLUBS)
        test_lib.add_reference(image=img_jc, card=card_jc)

        kc_suit_glyph = test_lib.extract_primary_glyph(img_kc[46:82, 8:44], (28, 28))
        pred_suit, suit_score, _ = test_lib.match_suit_glyph(kc_suit_glyph, is_red=False)

        assert pred_suit == Suit.CLUBS
        assert suit_score >= 0.85, f"Expected high suit correlation, got {suit_score}"

    def test_cross_learning_rank_k_from_kd_to_kc(self, test_lib):
        """Confirming KD provides rank glyph K, allowing instant identification of KC rank."""
        img_kd = self._load_fixture("KD")
        img_kc = self._load_fixture("KC")

        card_kd = Card(Rank.KING, Suit.DIAMONDS)
        test_lib.add_reference(image=img_kd, card=card_kd)

        kc_rank_glyph = test_lib.extract_primary_glyph(img_kc[8:48, 8:44], (24, 36))
        pred_rank, rank_score, _ = test_lib.match_rank_glyph(kc_rank_glyph)

        assert pred_rank == Rank.KING
        assert rank_score >= 0.88, f"Expected high rank correlation, got {rank_score}"

    def test_distinguish_jack_and_king_glyphs(self):
        """Rank J and Rank K have near-zero correlation and cannot be confused."""
        img_jc = self._load_fixture("JC")
        img_kc = self._load_fixture("KC")

        j_glyph = CardReferenceLibrary.extract_primary_glyph(img_jc[8:48, 8:44], (24, 36))
        k_glyph = CardReferenceLibrary.extract_primary_glyph(img_kc[8:48, 8:44], (24, 36))

        res = cv2.matchTemplate(j_glyph, k_glyph, cv2.TM_CCOEFF_NORMED)
        cross_score = float(res[0][0])
        assert cross_score < 0.10, f"Rank J and K should have low correlation, got {cross_score}"

    def test_distinguish_heart_and_diamond_suits(self):
        """Diamonds (♦) and Hearts (♥) are distinguished by symbol geometry despite both being red."""
        img_4h = self._load_fixture("4H")
        img_5d = self._load_fixture("5D")

        h_glyph = CardReferenceLibrary.extract_primary_glyph(img_4h[46:82, 8:44], (28, 28))
        d_glyph = CardReferenceLibrary.extract_primary_glyph(img_5d[46:82, 8:44], (28, 28))

        # Cross correlation between H and D
        res_hd = cv2.matchTemplate(h_glyph, d_glyph, cv2.TM_CCOEFF_NORMED)
        score_hd = float(res_hd[0][0])

        # Self correlation of D
        img_6d = self._load_fixture("6D")
        d2_glyph = CardReferenceLibrary.extract_primary_glyph(img_6d[46:82, 8:44], (28, 28))
        res_dd = cv2.matchTemplate(d_glyph, d2_glyph, cv2.TM_CCOEFF_NORMED)
        score_dd = float(res_dd[0][0])

        assert score_dd >= 0.95, f"Expected same suit correlation >= 0.95, got {score_dd}"
        assert (score_dd - score_hd) >= 0.35, "Clear separation margin between ♦ and ♥"

    def test_real_sample_leave_one_out_matching(self, test_lib):
        """Given one real 7D sample, accurately recognizes a second real 7D sample."""
        files_7d = sorted(self.FIXTURE_DIR.glob("7D*.png"))
        assert len(files_7d) >= 2, "Expected 2 samples of 7D"

        img_sample1 = cv2.imread(str(files_7d[0]))
        img_sample2 = cv2.imread(str(files_7d[1]))

        card_7d = Card(Rank.SEVEN, Suit.DIAMONDS)
        test_lib.add_reference(image=img_sample1, card=card_7d)

        recognizer = CardRecognizer(reference_library=test_lib)
        crop2 = CardCrop(
            bbox=(10, 10, 120, 168),
            image=img_sample2,
            corner_crop=img_sample2[0:70, 0:50],
            rank_crop=img_sample2[8:48, 8:44],
            suit_crop=img_sample2[46:82, 8:44],
        )

        detected = recognizer.recognize_crop(crop2)
        assert detected.card == card_7d
        assert detected.card_code == "7D"
        assert detected.rank_char == "7"
        assert detected.suit_char == "D"
        assert detected.rank_confidence >= 0.85
        assert detected.suit_confidence >= 0.85
        assert detected.overall_confidence >= 0.85
        assert detected.is_uncertain is False
        assert detected.is_reference_match is True

    def test_uncertain_flag_on_low_confidence_crop(self, test_lib):
        """When an unlearned, heavily corrupted or black crop is tested, is_uncertain is set."""
        recognizer = CardRecognizer(reference_library=test_lib)
        corrupted = np.full((168, 120, 3), 40, dtype=np.uint8)  # Dark noisy image

        crop = CardCrop(
            bbox=(0, 0, 120, 168),
            image=corrupted,
            corner_crop=corrupted[0:70, 0:50],
            rank_crop=corrupted[8:48, 8:44],
            suit_crop=corrupted[46:82, 8:44],
        )

        detected = recognizer.recognize_crop(crop)
        assert detected.is_uncertain is True
        assert len(detected.uncertain_reason) > 0


