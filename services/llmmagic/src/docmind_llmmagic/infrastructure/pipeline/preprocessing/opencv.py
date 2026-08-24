"""OpenCV-backed deterministic image preprocessing adapter."""

import asyncio
from concurrent.futures import Executor, ThreadPoolExecutor
from importlib import import_module
from typing import Any, cast

from docmind_llmmagic.application.pipeline.steps.document_preprocessing.errors import (
    DocumentPreprocessingPageError,
    safe_preprocessing_page_error,
)
from docmind_llmmagic.application.pipeline.steps.document_preprocessing.ports import (
    PreparedPageContent,
    TransformedPageContent,
)
from docmind_llmmagic.domain.pipeline.preflight import PreparedPageFormat
from docmind_llmmagic.domain.pipeline.preprocessing import (
    ImagePreprocessingConfig,
    ImageTransformationMetadata,
)

_PNG_EXTENSION = ".png"
_PNG_COMPRESSION = 3
_DESKEW_EPSILON_DEGREES = 0.01
_MAX_TRANSFORM_WORKERS = 2
_DEFAULT_TRANSFORM_EXECUTOR = ThreadPoolExecutor(
    max_workers=_MAX_TRANSFORM_WORKERS,
    thread_name_prefix="docmind-opencv-preprocessing",
)


class OpenCVPageImageTransformer:
    """Apply the first deterministic OCR preprocessing transform set with OpenCV."""

    def __init__(self, *, executor: Executor | None = None) -> None:
        self._cv2 = cast(Any, import_module("cv2"))
        self._np = cast(Any, import_module("numpy"))
        self._executor = executor or _DEFAULT_TRANSFORM_EXECUTOR

    async def transform_page(
        self,
        page: PreparedPageContent,
        config: ImagePreprocessingConfig,
    ) -> TransformedPageContent:
        """Transform one prepared page into a PNG artifact payload."""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, self._transform_page_sync, page, config)

    def _transform_page_sync(
        self,
        page: PreparedPageContent,
        config: ImagePreprocessingConfig,
    ) -> TransformedPageContent:
        try:
            image = self._decode(page.content)
            return self.transform_decoded_page(
                page=page,
                image=image,
                config=config,
            )
        except DocumentPreprocessingPageError:
            raise
        except Exception as exc:
            raise safe_preprocessing_page_error("PREPROCESSING_TRANSFORM_FAILED") from exc

    def transform_decoded_page(
        self,
        *,
        page: PreparedPageContent,
        image: Any,
        config: ImagePreprocessingConfig,
    ) -> TransformedPageContent:
        """Transform an already decoded page inside a caller-owned worker thread."""

        try:
            source_width_px, source_height_px = _dimensions(image)
            operation_codes: list[str] = []
            warning_codes: list[str] = []

            image, rotation_degrees = self._apply_rotation(
                image=image,
                rotation_degrees=config.rotation_degrees,
                operation_codes=operation_codes,
            )
            image, deskew_degrees = self._apply_deskew(
                image=image,
                config=config,
                operation_codes=operation_codes,
            )
            image = self._apply_grayscale(
                image=image,
                config=config,
                operation_codes=operation_codes,
            )
            image = self._apply_contrast(
                image=image,
                config=config,
                operation_codes=operation_codes,
            )
            image = self._apply_denoise(
                image=image,
                config=config,
                operation_codes=operation_codes,
            )
            image, scale, output_dpi = self._apply_dpi_normalization(
                image=image,
                page=page,
                config=config,
                operation_codes=operation_codes,
                warning_codes=warning_codes,
            )
            content = self._encode_png(image)
            output_width_px, output_height_px = _dimensions(image)

            return TransformedPageContent(
                page_number=page.page_number,
                content=content,
                width_px=output_width_px,
                height_px=output_height_px,
                format=PreparedPageFormat.PNG,
                dpi=output_dpi,
                transformation=ImageTransformationMetadata(
                    algorithm_version=config.algorithm_version,
                    preset_id=config.preset_id,
                    source_width_px=source_width_px,
                    source_height_px=source_height_px,
                    output_width_px=output_width_px,
                    output_height_px=output_height_px,
                    source_dpi=page.dpi,
                    output_dpi=output_dpi,
                    scale=scale,
                    rotation_degrees=rotation_degrees,
                    deskew_degrees=deskew_degrees,
                    format_normalized=config.normalize_format,
                    grayscale_applied=config.grayscale,
                    contrast_enhanced=config.enhance_contrast,
                    denoised=config.denoise,
                    operation_codes=tuple(operation_codes),
                    warning_codes=tuple(warning_codes),
                ),
            )
        except DocumentPreprocessingPageError:
            raise
        except Exception as exc:
            raise safe_preprocessing_page_error("PREPROCESSING_TRANSFORM_FAILED") from exc

    def _decode(self, content: bytes) -> Any:
        if not content:
            raise safe_preprocessing_page_error("PREPROCESSING_IMAGE_DECODE_FAILED")

        buffer = self._np.frombuffer(content, dtype=self._np.uint8)
        image = self._cv2.imdecode(buffer, self._cv2.IMREAD_COLOR)
        if image is None:
            raise safe_preprocessing_page_error("PREPROCESSING_IMAGE_DECODE_FAILED")

        return image

    def _apply_rotation(
        self,
        *,
        image: Any,
        rotation_degrees: float,
        operation_codes: list[str],
    ) -> tuple[Any, float]:
        if rotation_degrees == 0:
            return image, 0.0

        operation_codes.append("PREPROCESSING_ROTATED")
        return self._rotate(image, rotation_degrees), round(rotation_degrees, 4)

    def _apply_deskew(
        self,
        *,
        image: Any,
        config: ImagePreprocessingConfig,
        operation_codes: list[str],
    ) -> tuple[Any, float]:
        if not config.deskew:
            return image, 0.0

        angle = self._deskew_angle(image, max_degrees=config.max_deskew_degrees)
        if abs(angle) <= _DESKEW_EPSILON_DEGREES:
            return image, 0.0

        operation_codes.append("PREPROCESSING_DESKEWED")
        return self._rotate(image, angle), round(angle, 4)

    def _apply_grayscale(
        self,
        *,
        image: Any,
        config: ImagePreprocessingConfig,
        operation_codes: list[str],
    ) -> Any:
        if not config.grayscale or _is_grayscale(image):
            return image

        operation_codes.append("PREPROCESSING_GRAYSCALE")
        return self._cv2.cvtColor(image, self._cv2.COLOR_BGR2GRAY)

    def _apply_contrast(
        self,
        *,
        image: Any,
        config: ImagePreprocessingConfig,
        operation_codes: list[str],
    ) -> Any:
        if not config.enhance_contrast:
            return image

        operation_codes.append("PREPROCESSING_CONTRAST_ENHANCED")
        if _is_grayscale(image):
            clahe = self._cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            return clahe.apply(image)

        lab = self._cv2.cvtColor(image, self._cv2.COLOR_BGR2LAB)
        channels = list(self._cv2.split(lab))
        clahe = self._cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        channels[0] = clahe.apply(channels[0])
        merged = self._cv2.merge(channels)
        return self._cv2.cvtColor(merged, self._cv2.COLOR_LAB2BGR)

    def _apply_denoise(
        self,
        *,
        image: Any,
        config: ImagePreprocessingConfig,
        operation_codes: list[str],
    ) -> Any:
        if not config.denoise:
            return image

        operation_codes.append("PREPROCESSING_DENOISED")
        return self._cv2.bilateralFilter(
            image,
            config.bilateral_diameter,
            config.bilateral_sigma_color,
            config.bilateral_sigma_space,
        )

    def _apply_dpi_normalization(
        self,
        *,
        image: Any,
        page: PreparedPageContent,
        config: ImagePreprocessingConfig,
        operation_codes: list[str],
        warning_codes: list[str],
    ) -> tuple[Any, float, int | None]:
        if not config.normalize_dpi:
            return image, 1.0, page.dpi
        if page.dpi is None:
            warning_codes.append("PREPROCESSING_SOURCE_DPI_MISSING")
            return image, 1.0, None
        if page.dpi < 1:
            raise safe_preprocessing_page_error("PREPROCESSING_INPUT_ARTIFACT_INVALID")

        scale = config.target_dpi / page.dpi
        if scale == 1:
            return image, 1.0, config.target_dpi

        width_px, height_px = _dimensions(image)
        target_width_px, target_height_px = _scaled_dimensions(
            width_px=width_px,
            height_px=height_px,
            scale=scale,
        )
        _validate_target_dimensions(
            width_px=target_width_px,
            height_px=target_height_px,
            config=config,
        )
        resized = self._cv2.resize(
            image,
            (target_width_px, target_height_px),
            interpolation=self._cv2.INTER_CUBIC if scale > 1 else self._cv2.INTER_AREA,
        )
        operation_codes.append("PREPROCESSING_DPI_NORMALIZED")
        return resized, round(scale, 6), config.target_dpi

    def _deskew_angle(self, image: Any, *, max_degrees: float) -> float:
        gray = (
            image if _is_grayscale(image) else self._cv2.cvtColor(image, self._cv2.COLOR_BGR2GRAY)
        )
        _threshold, binary = self._cv2.threshold(
            gray,
            0,
            255,
            self._cv2.THRESH_BINARY_INV + self._cv2.THRESH_OTSU,
        )
        coordinates = self._cv2.findNonZero(binary)
        if coordinates is None:
            return 0.0

        angle = float(self._cv2.minAreaRect(coordinates)[-1])
        if angle < -45:
            angle = 90 + angle
        deskew_angle = -angle
        return max(-max_degrees, min(max_degrees, deskew_angle))

    def _rotate(self, image: Any, angle_degrees: float) -> Any:
        width_px, height_px = _dimensions(image)
        center = (width_px / 2, height_px / 2)
        matrix = self._cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
        return self._cv2.warpAffine(
            image,
            matrix,
            (width_px, height_px),
            flags=self._cv2.INTER_LINEAR,
            borderMode=self._cv2.BORDER_REPLICATE,
        )

    def _encode_png(self, image: Any) -> bytes:
        success, encoded = self._cv2.imencode(
            _PNG_EXTENSION,
            image,
            [self._cv2.IMWRITE_PNG_COMPRESSION, _PNG_COMPRESSION],
        )
        if not success:
            raise safe_preprocessing_page_error("PREPROCESSING_IMAGE_ENCODE_FAILED")

        return cast(bytes, encoded.tobytes())


def _dimensions(image: Any) -> tuple[int, int]:
    return int(image.shape[1]), int(image.shape[0])


def _scaled_dimensions(*, width_px: int, height_px: int, scale: float) -> tuple[int, int]:
    return max(1, round(width_px * scale)), max(1, round(height_px * scale))


def _validate_target_dimensions(
    *,
    width_px: int,
    height_px: int,
    config: ImagePreprocessingConfig,
) -> None:
    if width_px > config.max_page_width_px or height_px > config.max_page_height_px:
        raise safe_preprocessing_page_error("PREPROCESSING_OUTPUT_PAGE_TOO_LARGE")
    if (width_px * height_px) / 1_000_000 > config.max_page_megapixels:
        raise safe_preprocessing_page_error("PREPROCESSING_OUTPUT_PAGE_TOO_LARGE")


def _is_grayscale(image: Any) -> bool:
    return len(image.shape) == 2
