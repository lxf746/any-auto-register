from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import requests

from core.base_sms import HERO_SMS_DEFAULT_COUNTRY, HERO_SMS_DEFAULT_SERVICE, FiveSimProvider, GrizzlySmsProvider, HeroSmsProvider, SmsBowerProvider
from infrastructure.provider_settings_repository import ProviderSettingsRepository

router = APIRouter(prefix="/sms", tags=["sms"])


class HeroSmsQueryRequest(BaseModel):
    api_key: str = ""
    service: str = ""
    country: str = ""
    proxy: str = ""


class FiveSimQueryRequest(BaseModel):
    api_key: str = ""
    country: str = ""
    operator: str = "any"
    product: str = ""
    proxy: str = ""


def _saved_fivesim_config() -> dict:
    repo = ProviderSettingsRepository()
    config = repo.resolve_runtime_settings("sms", "fivesim_api", {})
    if not config.get("fivesim_api_key"):
        # 兼容可能的旧 key
        config = repo.resolve_runtime_settings("sms", "fivesim", {})
    return config


def _fivesim_from_payload(payload: FiveSimQueryRequest | None = None) -> FiveSimProvider:
    payload = payload or FiveSimQueryRequest()
    saved = _saved_fivesim_config()
    api_key = str(payload.api_key or saved.get("fivesim_api_key") or saved.get("5sim_api_key") or "").strip()
    return FiveSimProvider(
        api_key=api_key,
        default_country=str(payload.country or saved.get("fivesim_default_country") or saved.get("fivesim_country") or "any"),
        default_operator=str(payload.operator or saved.get("fivesim_default_operator") or "any"),
        default_product=str(payload.product or saved.get("fivesim_default_product") or ""),
        proxy=str(payload.proxy or saved.get("sms_proxy") or saved.get("proxy") or "") or None,
    )


def _saved_herosms_config() -> dict:
    repo = ProviderSettingsRepository()
    # 兼容旧版 provider_key "herosms" 和新版 "herosms_api"
    config = repo.resolve_runtime_settings("sms", "herosms_api", {})
    if not config.get("herosms_api_key"):
        config = repo.resolve_runtime_settings("sms", "herosms", {})
    return config


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _provider_from_payload(payload: HeroSmsQueryRequest | None = None) -> HeroSmsProvider:
    payload = payload or HeroSmsQueryRequest()
    saved = _saved_herosms_config()
    api_key = str(payload.api_key or saved.get("herosms_api_key") or "").strip()
    return HeroSmsProvider(
        api_key=api_key,
        default_service=str(payload.service or saved.get("sms_service") or HERO_SMS_DEFAULT_SERVICE),
        default_country=str(payload.country or saved.get("sms_country") or HERO_SMS_DEFAULT_COUNTRY),
        max_price=_safe_float(saved.get("herosms_max_price"), -1),
        proxy=str(payload.proxy or saved.get("sms_proxy") or saved.get("proxy") or "") or None,
    )


@router.get("/herosms/countries")
def herosms_countries():
    try:
        return {"countries": _provider_from_payload().get_countries()}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/herosms/services")
def herosms_services(country: str = ""):
    try:
        return {"services": _provider_from_payload(HeroSmsQueryRequest(country=country)).get_services(country=country or None)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.post("/herosms/balance")
def herosms_balance(body: HeroSmsQueryRequest | None = None):
    body = body or HeroSmsQueryRequest()
    provider = _provider_from_payload(body)
    if not provider.api_key:
        raise HTTPException(400, "HeroSMS API Key 未配置")
    try:
        return {"balance": provider.get_balance()}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.post("/herosms/prices")
def herosms_prices(body: HeroSmsQueryRequest | None = None):
    body = body or HeroSmsQueryRequest()
    provider = _provider_from_payload(body)
    if not provider.api_key:
        raise HTTPException(400, "HeroSMS API Key 未配置")
    try:
        service = str(body.service or provider.default_service or HERO_SMS_DEFAULT_SERVICE)
        country = str(body.country or provider.default_country or HERO_SMS_DEFAULT_COUNTRY)
        return {"prices": provider.get_prices(service=service, country=country)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


class HeroSmsBestCountryRequest(BaseModel):
    api_key: str = ""
    service: str = ""
    proxy: str = ""
    min_stock: int = 20
    max_price: float = 0
    top_n: int = 10


@router.post("/herosms/top-countries")
def herosms_top_countries(body: HeroSmsBestCountryRequest | None = None):
    """获取按价格排序的国家列表（含价格和库存）。"""
    body = body or HeroSmsBestCountryRequest()
    provider = _provider_from_payload(HeroSmsQueryRequest(
        api_key=body.api_key, service=body.service, proxy=body.proxy,
    ))
    if not provider.api_key:
        raise HTTPException(400, "HeroSMS API Key 未配置")
    try:
        service = str(body.service or provider.default_service or HERO_SMS_DEFAULT_SERVICE)
        rows = provider.get_top_countries(service=service)
        # 只返回有库存的
        rows = [r for r in rows if (r.get("count") or 0) > 0]
        if body.top_n > 0:
            rows = rows[:body.top_n]
        return {"countries": rows, "service": service}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.post("/herosms/best-country")
def herosms_best_country(body: HeroSmsBestCountryRequest | None = None):
    """自动选择最优国家（价格最低 + 库存充足）。"""
    body = body or HeroSmsBestCountryRequest()
    provider = _provider_from_payload(HeroSmsQueryRequest(
        api_key=body.api_key, service=body.service, proxy=body.proxy,
    ))
    if not provider.api_key:
        raise HTTPException(400, "HeroSMS API Key 未配置")
    try:
        service = str(body.service or provider.default_service or HERO_SMS_DEFAULT_SERVICE)
        best = provider.get_best_country(
            service=service,
            min_stock=body.min_stock,
            max_price=body.max_price,
        )
        if best:
            # 获取详细信息
            rows = provider.get_top_countries(service=service)
            detail = next((r for r in rows if str(r.get("country")) == str(best)), None)
            return {
                "country": best,
                "detail": detail,
                "service": service,
            }
        return {"country": None, "detail": None, "service": service}
    except Exception as exc:
        raise HTTPException(502, str(exc))


# ── SMSBower endpoints ──────────────────────────────────────────────────────

def _saved_smsbower_config() -> dict:
    return ProviderSettingsRepository().resolve_runtime_settings("sms", "smsbower_api", {})


def _smsbower_from_payload(payload: HeroSmsQueryRequest | None = None) -> SmsBowerProvider:
    payload = payload or HeroSmsQueryRequest()
    saved = _saved_smsbower_config()
    api_key = str(payload.api_key or saved.get("smsbower_api_key") or "").strip()
    return SmsBowerProvider(
        api_key=api_key,
        default_service=str(payload.service or saved.get("sms_service") or saved.get("smsbower_service") or HERO_SMS_DEFAULT_SERVICE),
        default_country=str(payload.country or saved.get("sms_country") or saved.get("smsbower_country") or HERO_SMS_DEFAULT_COUNTRY),
        max_price=_safe_float(saved.get("smsbower_max_price"), -1),
        proxy=str(payload.proxy or saved.get("sms_proxy") or saved.get("proxy") or "") or None,
    )


@router.get("/smsbower/countries")
def smsbower_countries():
    try:
        provider = _smsbower_from_payload()
        if not provider.api_key:
            return {"countries": []}
        return {"countries": provider.get_countries()}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/smsbower/services")
def smsbower_services(country: str = ""):
    try:
        provider = _smsbower_from_payload(HeroSmsQueryRequest(country=country))
        if not provider.api_key:
            return {"services": []}
        return {"services": provider.get_services(country=country or None)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.post("/smsbower/balance")
def smsbower_balance(body: HeroSmsQueryRequest | None = None):
    body = body or HeroSmsQueryRequest()
    provider = _smsbower_from_payload(body)
    if not provider.api_key:
        raise HTTPException(400, "SMSBower API Key 未配置")
    try:
        return {"balance": provider.get_balance()}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.post("/smsbower/prices")
def smsbower_prices(body: HeroSmsQueryRequest | None = None):
    body = body or HeroSmsQueryRequest()
    provider = _smsbower_from_payload(body)
    if not provider.api_key:
        raise HTTPException(400, "SMSBower API Key 未配置")
    try:
        service = str(body.service or provider.default_service or HERO_SMS_DEFAULT_SERVICE)
        country = str(body.country or provider.default_country or HERO_SMS_DEFAULT_COUNTRY)
        return {"prices": provider.get_prices(service=service, country=country)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


# ── GrizzlySMS endpoints ────────────────────────────────────────────────────

def _saved_grizzlysms_config() -> dict:
    return ProviderSettingsRepository().resolve_runtime_settings("sms", "grizzlysms_api", {})


def _grizzlysms_from_payload(payload: HeroSmsQueryRequest | None = None) -> GrizzlySmsProvider:
    payload = payload or HeroSmsQueryRequest()
    saved = _saved_grizzlysms_config()
    api_key = str(payload.api_key or saved.get("grizzlysms_api_key") or "").strip()
    return GrizzlySmsProvider(
        api_key=api_key,
        default_service=str(payload.service or saved.get("sms_service") or saved.get("grizzlysms_service") or HERO_SMS_DEFAULT_SERVICE),
        default_country=str(payload.country or saved.get("sms_country") or saved.get("grizzlysms_country") or HERO_SMS_DEFAULT_COUNTRY),
        max_price=_safe_float(saved.get("grizzlysms_max_price"), -1),
        proxy=str(payload.proxy or saved.get("sms_proxy") or saved.get("proxy") or "") or None,
    )


@router.get("/grizzlysms/countries")
def grizzlysms_countries():
    try:
        provider = _grizzlysms_from_payload()
        if not provider.api_key:
            return {"countries": []}
        return {"countries": provider.get_countries()}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/grizzlysms/services")
def grizzlysms_services(country: str = ""):
    try:
        provider = _grizzlysms_from_payload(HeroSmsQueryRequest(country=country))
        if not provider.api_key:
            return {"services": []}
        return {"services": provider.get_services(country=country or None)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.post("/grizzlysms/balance")
def grizzlysms_balance(body: HeroSmsQueryRequest | None = None):
    body = body or HeroSmsQueryRequest()
    provider = _grizzlysms_from_payload(body)
    if not provider.api_key:
        raise HTTPException(400, "GrizzlySMS API Key 未配置")
    try:
        return {"balance": provider.get_balance()}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.post("/grizzlysms/prices")
def grizzlysms_prices(body: HeroSmsQueryRequest | None = None):
    body = body or HeroSmsQueryRequest()
    provider = _grizzlysms_from_payload(body)
    if not provider.api_key:
        raise HTTPException(400, "GrizzlySMS API Key 未配置")
    try:
        service = str(body.service or provider.default_service or HERO_SMS_DEFAULT_SERVICE)
        country = str(body.country or provider.default_country or HERO_SMS_DEFAULT_COUNTRY)
        return {"prices": provider.get_prices(service=service, country=country)}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/grizzlysms/countries_with_prices")
def grizzlysms_countries_with_prices(service: str = ""):
    """
    返回国家列表，每条记录的 chn 字段附带该 service 的价格。

    GrizzlySMS getPrices(service=xxx) 返回格式：
      { "1": {"ot": {"cost": 0.46, "count": 2017, "retry": 0}}, ... }
    """
    try:
        provider = _grizzlysms_from_payload(HeroSmsQueryRequest(service=service))
        if not provider.api_key:
            return {"countries": []}

        service_code = str(service or provider.default_service or HERO_SMS_DEFAULT_SERVICE).strip()

        # 构建 country_id -> price 映射
        # getPrices 只传 service，返回: {cid: {service_code: {"cost": 0.46, ...}}}
        price_map: dict[str, float] = {}
        try:
            prices = provider.get_prices(service=service_code)
            if isinstance(prices, dict):
                for cid, svc_map in prices.items():
                    if not isinstance(svc_map, dict):
                        continue
                    inner = svc_map.get(service_code) or svc_map.get(str(service_code))
                    if isinstance(inner, dict):
                        cost = inner.get("cost") or inner.get("price") or inner.get("retail_price")
                        if cost is not None:
                            try:
                                price_map[str(cid)] = float(cost)
                            except (TypeError, ValueError):
                                pass
        except Exception:
            pass

        # 拉所有国家基础信息（含 chn 中文名）
        countries = []
        try:
            countries = provider.get_countries() or []
        except Exception:
            pass

        out = []
        for c in countries:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("id") or c.get("country") or c.get("code") or "").strip()
            if not cid:
                continue
            chn = str(c.get("chn") or c.get("eng") or c.get("name") or c.get("title") or cid).strip()
            p = price_map.get(cid)
            if p is not None:
                chn = f"{chn} \xa5{p}"
            out.append({"id": cid, "chn": chn})

        # 有价格的国家排前面，按价格升序
        out.sort(key=lambda x: (0 if x["id"] in price_map else 1, price_map.get(x["id"]) or 999))

        return {"countries": out}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/fivesim/countries")
def fivesim_countries():
    """Guest: 获取国家列表。"""
    try:
        # docs 未完整展示，但社区与 SDK 均使用该路径
        r = requests.get("https://5sim.net/v1/guest/countries", headers={"accept": "application/json"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        # 返回结构可能是 dict(country_code -> {...})，也可能是 list
        out = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, dict):
                    name = str(v.get("name") or v.get("title") or v.get("country") or k)
                else:
                    name = str(v or k)
                out.append({"code": str(k), "name": name})
        elif isinstance(data, list):
            for it in data:
                if isinstance(it, dict):
                    code = str(it.get("code") or it.get("country") or it.get("id") or "")
                    if not code:
                        continue
                    out.append({"code": code, "name": str(it.get("name") or it.get("title") or code)})
        return {"countries": out}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/fivesim/operators")
def fivesim_operators(country: str = ""):
    """Guest: 获取运营商列表（依赖国家）。"""
    try:
        c = str(country or "any").strip()
        r = requests.get(f"https://5sim.net/v1/guest/operators/{c}", headers={"accept": "application/json"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        out = []
        if isinstance(data, dict):
            for k, v in data.items():
                out.append({"code": str(k), "name": str((v.get("name") if isinstance(v, dict) else v) or k)})
        elif isinstance(data, list):
            for it in data:
                if isinstance(it, str):
                    out.append({"code": it, "name": it})
                elif isinstance(it, dict):
                    code = str(it.get("code") or it.get("operator") or it.get("id") or "")
                    if code:
                        out.append({"code": code, "name": str(it.get("name") or code)})
        # 保证 any 在最前
        out = [o for o in out if o["code"] == "any"] + [o for o in out if o["code"] != "any"]
        return {"operators": out}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/fivesim/products")
def fivesim_products(country: str = "", operator: str = "any"):
    """Guest: 获取该国家/运营商支持的 products。"""
    try:
        # 5sim 的 products API 必须传 country；为了支持“先选项目”，这里给一个稳定默认值
        # （英国通常覆盖最全，且用户可在任务里自行覆盖 country/operator）。
        c = str(country or "england").strip()
        op = str(operator or "any").strip()
        r = requests.get(f"https://5sim.net/v1/guest/products/{c}/{op}", headers={"accept": "application/json"}, timeout=20)
        r.raise_for_status()
        data = r.json()
        out = []
        # 通常格式: {product_name: {Price/qty...}, ...}
        if isinstance(data, dict):
            for k in data.keys():
                out.append({"code": str(k), "name": str(k)})
        elif isinstance(data, list):
            for it in data:
                if isinstance(it, str):
                    out.append({"code": it, "name": it})
                elif isinstance(it, dict):
                    code = str(it.get("code") or it.get("product") or it.get("name") or "")
                    if code:
                        out.append({"code": code, "name": str(it.get("title") or code)})
        return {"products": out}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.post("/fivesim/balance")
def fivesim_balance(body: FiveSimQueryRequest | None = None):
    body = body or FiveSimQueryRequest()
    provider = _fivesim_from_payload(body)
    if not provider.api_key:
        raise HTTPException(400, "5sim API Key 未配置")
    try:
        return {"balance": provider.get_balance()}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@router.get("/fivesim/countries_with_prices")
def fivesim_countries_with_prices(product: str = ""):
    """按 product 反查可用国家，并把最低价格拼到 name 字段里。"""
    try:
        p = str(product or "").strip()
        if not p:
            return {"countries": []}
        # 关键：prices?product=xxx 返回结构：
        # { product: { country: { operator: {cost,count,...} } } }
        r = requests.get(
            f"https://5sim.net/v1/guest/prices",
            params={"product": p},
            headers={"accept": "application/json", "user-agent": "Mozilla/5.0"},
            timeout=25,
        )
        r.raise_for_status()
        data = r.json()
        by_prod = data.get(p) if isinstance(data, dict) else None
        if not isinstance(by_prod, dict):
            return {"countries": []}

        out = []
        for country_code, op_map in by_prod.items():
            if not isinstance(op_map, dict):
                continue
            # 取该国家所有 operator 里 cost 最小的那个
            best_cost = None
            best_count = None
            for _op, v in op_map.items():
                if not isinstance(v, dict):
                    continue
                cost = v.get("cost")
                cnt = v.get("count")
                try:
                    cost_f = float(cost) if cost is not None else None
                except (TypeError, ValueError):
                    cost_f = None
                try:
                    cnt_i = int(cnt) if cnt is not None else 0
                except (TypeError, ValueError):
                    cnt_i = 0
                if cost_f is None:
                    continue
                if best_cost is None or cost_f < best_cost:
                    best_cost = cost_f
                    best_count = cnt_i

            if best_cost is None:
                continue
            # 仅把有库存的排前面（但仍返回所有国家，避免误判）
            name = f"{country_code} ¥{best_cost}"
            if best_count is not None:
                name = f"{name} (stock {best_count})"
            out.append({"code": str(country_code), "name": name})

        # 有库存的排前，按价格升序
        def _sort_key(x):
            m = __import__("re").search(r"stock\\s+(\\d+)", str(x.get("name") or ""))
            stock = int(m.group(1)) if m else 0
            m2 = __import__("re").search(r"¥([0-9.]+)", str(x.get("name") or ""))
            price = float(m2.group(1)) if m2 else 999.0
            return (0 if stock > 0 else 1, price)

        out.sort(key=_sort_key)
        return {"countries": out, "product": p}
    except Exception as exc:
        raise HTTPException(502, str(exc))
