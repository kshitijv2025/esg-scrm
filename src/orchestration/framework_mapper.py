"""
FrameworkMappingEngine — maps canonical DataPoints to framework-specific disclosures.

SPEC 01: https://github.com/kshitijv2025/esg-scrm/blob/main/specs/01-data-orchestration.md
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

import structlog

from src.orchestration.disclosure_package import (
    ConfidenceSummary,
    DataPoint,
    DataPointType,
    DisclosurePackage,
    FrameworkType,
    Gap,
)

logger = structlog.get_logger(__name__)

# DefaultScope3 spend-based emission factors (kgCO2e per USD)
# Source: EPA EEIO 2023 — industry average
DEFAULT_SCOPE3_EMISSION_FACTOR_KGCO2E_PER_USD = float(
    os.environ.get("SCOPE3_EMISSION_FACTOR_KGCO2E_PER_USD", "0.5")
)


@dataclass
class FrameworkMappingEngine:
    """Maps canonical DataPoints to framework-specific disclosure packages.

    Each framework mapper transforms DataPoints into a DisclosurePackage
    with framework-specific disclosure codes and gap analysis.
    """

    scope3_emission_factor: float = DEFAULT_SCOPE3_EMISSION_FACTOR_KGCO2E_PER_USD

    def map_to_csrd(
        self,
        data_points: list[DataPoint],
        organization_id: UUID,
        reporting_period: tuple[date, date],
    ) -> DisclosurePackage:
        """Map DataPoints to CSRD/ESRS disclosure package.

        Maps to ESRS categories:
        - E1: Climate change (energy, emissions)
        - E2: Pollution (water, waste)
        - E3: Water and marine resources
        - S1: Own workforce (employee data)
        - S2: Workers in value chain (supply chain)
        - G1: Business conduct (governance)

        Args:
            data_points: List of canonical DataPoints to map.
            organization_id: UUID of the reporting organization.
            reporting_period: Tuple of (start_date, end_date).

        Returns:
            A DisclosurePackage with CSRD-specific disclosure codes and gaps.
        """
        logger.info(
            "framework_map.csrd.start",
            organization_id=str(organization_id),
            data_points_count=len(data_points),
        )

        csrd_data_points = []
        gaps = []

        # E1 — Energy and emissions
        energy_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.ENERGY_KWH]
        scope1_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.SCOPE1_TCO2E]
        scope2_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.SCOPE2_TCO2E]
        scope3_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.SCOPE3_TCO2E]

        if not energy_dps and not scope1_dps and not scope2_dps and not scope3_dps:
            gaps.append(
                Gap(
                    gap_id="CSRD-E1-001",
                    data_point_type=DataPointType.ENERGY_KWH,
                    framework_disclosure_code="ESRS E1",
                    description="No energy or emissions data available for E1 disclosure",
                    severity="HIGH",
                    suggested_improvement="Install submeters or link to utility provider API",
                )
            )

        # E2 — Pollution (water, waste)
        water_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.WATER_M3]
        waste_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.WASTE_KG]

        if not water_dps:
            gaps.append(
                Gap(
                    gap_id="CSRD-E3-001",
                    data_point_type=DataPointType.WATER_M3,
                    framework_disclosure_code="ESRS E3",
                    description="No water consumption data available for E3 disclosure",
                    severity="MEDIUM",
                    suggested_improvement="Link to water utility billing system",
                )
            )

        if not waste_dps:
            gaps.append(
                Gap(
                    gap_id="CSRD-E2-001",
                    data_point_type=DataPointType.WASTE_KG,
                    framework_disclosure_code="ESRS E2",
                    description="No waste data available for E2 disclosure",
                    severity="MEDIUM",
                    suggested_improvement="Implement waste tracking system",
                )
            )

        # S1 — Own workforce
        headcount_dps = [
            dp for dp in data_points if dp.data_point_type == DataPointType.EMPLOYEE_HEADCOUNT
        ]
        turnover_dps = [
            dp for dp in data_points if dp.data_point_type == DataPointType.EMPLOYEE_TURNOVER_RATE
        ]

        if not headcount_dps:
            gaps.append(
                Gap(
                    gap_id="CSRD-S1-001",
                    data_point_type=DataPointType.EMPLOYEE_HEADCOUNT,
                    framework_disclosure_code="ESRS S1",
                    description="No employee headcount data available for S1 disclosure",
                    severity="MEDIUM",
                    suggested_improvement="Connect to HRIS system",
                )
            )

        # S2 — Supply chain (Scope 3)
        if not scope3_dps:
            gaps.append(
                Gap(
                    gap_id="CSRD-S2-001",
                    data_point_type=DataPointType.SCOPE3_TCO2E,
                    framework_disclosure_code="ESRS S2",
                    description="No Scope 3 supply chain data available for S2 disclosure",
                    severity="HIGH",
                    suggested_improvement="Implement supplier questionnaire program",
                )
            )

        csrd_data_points.extend(energy_dps)
        csrd_data_points.extend(scope1_dps)
        csrd_data_points.extend(scope2_dps)
        csrd_data_points.extend(scope3_dps)
        csrd_data_points.extend(water_dps)
        csrd_data_points.extend(waste_dps)
        csrd_data_points.extend(headcount_dps)
        csrd_data_points.extend(turnover_dps)

        confidence = self._compute_confidence_summary(csrd_data_points)

        package = DisclosurePackage(
            framework=FrameworkType.CSRD,
            reporting_period=reporting_period,
            organization_id=organization_id,
            data_points=csrd_data_points,
            generated_at=datetime.utcnow(),
            confidence_summary=confidence,
            gaps=gaps,
            disclosure_id=f"CSRD-{reporting_period[0].year}-{(reporting_period[1] - reporting_period[0]).days // 90 + 1}Q",
        )

        logger.info(
            "framework_map.csrd.complete",
            disclosure_id=package.disclosure_id,
            data_points_count=len(csrd_data_points),
            gaps_count=len(gaps),
            confidence_high_pct=confidence.high_pct,
        )

        return package

    def map_to_issb(
        self,
        data_points: list[DataPoint],
        organization_id: UUID,
        reporting_period: tuple[date, date],
    ) -> DisclosurePackage:
        """Map DataPoints to ISSB (IFRS S1/S2) disclosure package.

        Maps to ISSB climate-related disclosures:
        - S1: Governance — climate risks oversight
        - S2: Strategy — climate-related risks and opportunities
        - S2: Metrics and targets — climate metrics

        Args:
            data_points: List of canonical DataPoints to map.
            organization_id: UUID of the reporting organization.
            reporting_period: Tuple of (start_date, end_date).

        Returns:
            A DisclosurePackage with ISSB-specific disclosure codes and gaps.
        """
        logger.info(
            "framework_map.issb.start",
            organization_id=str(organization_id),
            data_points_count=len(data_points),
        )

        issb_data_points = []
        gaps = []

        # ISSB S1/S2 — Climate metrics
        energy_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.ENERGY_KWH]
        emissions_dps = [
            dp
            for dp in data_points
            if dp.data_point_type
            in (DataPointType.SCOPE1_TCO2E, DataPointType.SCOPE2_TCO2E, DataPointType.SCOPE3_TCO2E)
        ]

        if not energy_dps:
            gaps.append(
                Gap(
                    gap_id="ISSB-S2-001",
                    data_point_type=DataPointType.ENERGY_KWH,
                    framework_disclosure_code="ISSB S2",
                    description="No energy consumption data for climate metrics",
                    severity="HIGH",
                    suggested_improvement="Install energy submetering",
                )
            )

        if not emissions_dps:
            gaps.append(
                Gap(
                    gap_id="ISSB-S2-002",
                    data_point_type=DataPointType.SCOPE1_TCO2E,
                    framework_disclosure_code="ISSB S2",
                    description="No emissions data available for climate risk disclosure",
                    severity="HIGH",
                    suggested_improvement="Conduct GHG inventory",
                )
            )

        issb_data_points.extend(energy_dps)
        issb_data_points.extend(emissions_dps)

        confidence = self._compute_confidence_summary(issb_data_points)

        package = DisclosurePackage(
            framework=FrameworkType.ISSB,
            reporting_period=reporting_period,
            organization_id=organization_id,
            data_points=issb_data_points,
            generated_at=datetime.utcnow(),
            confidence_summary=confidence,
            gaps=gaps,
            disclosure_id=f"ISSB-{reporting_period[0].year}",
        )

        logger.info(
            "framework_map.issb.complete",
            disclosure_id=package.disclosure_id,
            data_points_count=len(issb_data_points),
            gaps_count=len(gaps),
        )

        return package

    def map_to_gri(
        self,
        data_points: list[DataPoint],
        organization_id: UUID,
        reporting_period: tuple[date, date],
    ) -> DisclosurePackage:
        """Map DataPoints to GRI disclosure package.

        Maps to GRI standards:
        - GRI 302: Energy
        - GRI 303: Water and effluents
        - GRI 305: Emissions
        - GRI 306: Waste
        - GRI 405: Diversity and equal opportunity

        Args:
            data_points: List of canonical DataPoints to map.
            organization_id: UUID of the reporting organization.
            reporting_period: Tuple of (start_date, end_date).

        Returns:
            A DisclosurePackage with GRI-specific disclosure codes and gaps.
        """
        logger.info(
            "framework_map.gri.start",
            organization_id=str(organization_id),
            data_points_count=len(data_points),
        )

        gri_data_points = []
        gaps = []

        # GRI 302 — Energy
        energy_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.ENERGY_KWH]
        if not energy_dps:
            gaps.append(
                Gap(
                    gap_id="GRI-302-001",
                    data_point_type=DataPointType.ENERGY_KWH,
                    framework_disclosure_code="GRI 302",
                    description="No energy consumption data for GRI 302 disclosure",
                    severity="HIGH",
                    suggested_improvement="Link to utility provider data",
                )
            )

        # GRI 303 — Water
        water_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.WATER_M3]
        if not water_dps:
            gaps.append(
                Gap(
                    gap_id="GRI-303-001",
                    data_point_type=DataPointType.WATER_M3,
                    framework_disclosure_code="GRI 303",
                    description="No water consumption data for GRI 303 disclosure",
                    severity="MEDIUM",
                    suggested_improvement="Install water meters or connect to utility API",
                )
            )

        # GRI 305 — Emissions
        emissions_dps = [
            dp
            for dp in data_points
            if dp.data_point_type
            in (
                DataPointType.SCOPE1_TCO2E,
                DataPointType.SCOPE2_TCO2E,
                DataPointType.SCOPE3_TCO2E,
            )
        ]
        if not emissions_dps:
            gaps.append(
                Gap(
                    gap_id="GRI-305-001",
                    data_point_type=DataPointType.SCOPE1_TCO2E,
                    framework_disclosure_code="GRI 305",
                    description="No emissions data for GRI 305 disclosure",
                    severity="HIGH",
                    suggested_improvement="Conduct Scope 1/2/3 GHG inventory",
                )
            )

        # GRI 306 — Waste
        waste_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.WASTE_KG]
        if not waste_dps:
            gaps.append(
                Gap(
                    gap_id="GRI-306-001",
                    data_point_type=DataPointType.WASTE_KG,
                    framework_disclosure_code="GRI 306",
                    description="No waste data for GRI 306 disclosure",
                    severity="MEDIUM",
                    suggested_improvement="Implement waste tracking",
                )
            )

        gri_data_points.extend(energy_dps)
        gri_data_points.extend(water_dps)
        gri_data_points.extend(emissions_dps)
        gri_data_points.extend(waste_dps)

        confidence = self._compute_confidence_summary(gri_data_points)

        package = DisclosurePackage(
            framework=FrameworkType.GRI,
            reporting_period=reporting_period,
            organization_id=organization_id,
            data_points=gri_data_points,
            generated_at=datetime.utcnow(),
            confidence_summary=confidence,
            gaps=gaps,
            disclosure_id=f"GRI-{reporting_period[0].year}",
        )

        logger.info(
            "framework_map.gri.complete",
            disclosure_id=package.disclosure_id,
            data_points_count=len(gri_data_points),
            gaps_count=len(gaps),
        )

        return package

    def map_to_tcfd(
        self,
        data_points: list[DataPoint],
        organization_id: UUID,
        reporting_period: tuple[date, date],
    ) -> DisclosurePackage:
        """Map DataPoints to TCFD disclosure package.

        Maps to TCFD four pillars:
        - Governance: Climate risks oversight
        - Strategy: Climate-related risks and opportunities
        - Risk Management: Climate risk identification and assessment
        - Metrics and Targets: Climate metrics and targets

        Args:
            data_points: List of canonical DataPoints to map.
            organization_id: UUID of the reporting organization.
            reporting_period: Tuple of (start_date, end_date).

        Returns:
            A DisclosurePackage with TCFD-specific disclosure codes and gaps.
        """
        logger.info(
            "framework_map.tcfd.start",
            organization_id=str(organization_id),
            data_points_count=len(data_points),
        )

        tcfd_data_points = []
        gaps = []

        # TCFD Metrics and Targets — energy and emissions
        energy_dps = [dp for dp in data_points if dp.data_point_type == DataPointType.ENERGY_KWH]
        emissions_dps = [
            dp
            for dp in data_points
            if dp.data_point_type
            in (
                DataPointType.SCOPE1_TCO2E,
                DataPointType.SCOPE2_TCO2E,
                DataPointType.SCOPE3_TCO2E,
            )
        ]

        if not energy_dps:
            gaps.append(
                Gap(
                    gap_id="TCFD-MT-001",
                    data_point_type=DataPointType.ENERGY_KWH,
                    framework_disclosure_code="TCFD Metrics & Targets",
                    description="No energy data for TCFD metrics disclosure",
                    severity="HIGH",
                    suggested_improvement="Implement energy monitoring",
                )
            )

        if not emissions_dps:
            gaps.append(
                Gap(
                    gap_id="TCFD-MT-002",
                    data_point_type=DataPointType.SCOPE1_TCO2E,
                    framework_disclosure_code="TCFD Metrics & Targets",
                    description="No emissions data for TCFD metrics and targets",
                    severity="HIGH",
                    suggested_improvement="Complete GHG inventory",
                )
            )

        tcfd_data_points.extend(energy_dps)
        tcfd_data_points.extend(emissions_dps)

        confidence = self._compute_confidence_summary(tcfd_data_points)

        package = DisclosurePackage(
            framework=FrameworkType.TCFD,
            reporting_period=reporting_period,
            organization_id=organization_id,
            data_points=tcfd_data_points,
            generated_at=datetime.utcnow(),
            confidence_summary=confidence,
            gaps=gaps,
            disclosure_id=f"TCFD-{reporting_period[0].year}",
        )

        logger.info(
            "framework_map.tcfd.complete",
            disclosure_id=package.disclosure_id,
            data_points_count=len(tcfd_data_points),
            gaps_count=len(gaps),
        )

        return package

    def _compute_confidence_summary(self, data_points: list[DataPoint]) -> ConfidenceSummary:
        """Compute confidence summary for a list of data points."""
        if not data_points:
            return ConfidenceSummary(high_pct=0.0, medium_pct=0.0, low_pct=0.0, total_data_points=0)

        total = len(data_points)
        high_count = sum(1 for dp in data_points if dp.confidence == "HIGH")
        medium_count = sum(1 for dp in data_points if dp.confidence == "MEDIUM")
        low_count = sum(1 for dp in data_points if dp.confidence == "LOW")

        return ConfidenceSummary(
            high_pct=round(high_count / total * 100, 2),
            medium_pct=round(medium_count / total * 100, 2),
            low_pct=round(low_count / total * 100, 2),
            total_data_points=total,
        )
