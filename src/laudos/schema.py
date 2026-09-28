"""Uniform, strict extraction result for property appraisal reports."""

from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


T = TypeVar("T")
PropertyType = Literal[
    "apartamento", "casa", "sala_comercial", "terreno", "imovel_rural",
    "loja", "galpao", "unidade_comercial",
]
Confidence = Literal["baixa", "media", "alta"]


class Evidence(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid", strict=True)
    value: T | None = None
    evidencia: str | None = None
    confianca: Confidence | None = None

    @field_validator("evidencia")
    @classmethod
    def nonempty_evidence(cls, value: str | None) -> str | None:
        return value if value else None


class Appraisal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tipo_imovel: Evidence[PropertyType] = Field(default_factory=Evidence[PropertyType])
    endereco: Evidence[str] = Field(default_factory=Evidence[str])
    area_privativa_m2: Evidence[float] = Field(default_factory=Evidence[float])
    area_total_m2: Evidence[float] = Field(default_factory=Evidence[float])
    area_terreno_m2: Evidence[float] = Field(default_factory=Evidence[float])
    area_construida_m2: Evidence[float] = Field(default_factory=Evidence[float])
    ano_construcao: Evidence[int] = Field(default_factory=Evidence[int])
    valor_avaliacao_brl: Evidence[float] = Field(default_factory=Evidence[float])
    matricula: Evidence[str] = Field(default_factory=Evidence[str])
    onus: Evidence[str] = Field(default_factory=Evidence[str])
    tem_onus: Evidence[bool] = Field(default_factory=Evidence[bool])
    data_vistoria: Evidence[str] = Field(default_factory=Evidence[str])
    responsavel_tecnico: Evidence[str] = Field(default_factory=Evidence[str])
    registro_profissional: Evidence[str] = Field(default_factory=Evidence[str])
    avisos: list[str] = Field(default_factory=list)


TARGET_FIELDS = tuple(name for name in Appraisal.model_fields if name != "avisos")
