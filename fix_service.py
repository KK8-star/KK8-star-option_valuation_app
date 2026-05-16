with open('src/services/valuation_service.py', encoding='utf-8') as f:
    content = f.read()

# ─── _binomial 修正 ───
old_bin = '''def _binomial(p: ValuationParams) -> float:
    S, K, r, σ, T, q, N = (p.stock_price, p.strike_price, p.risk_free_rate,
                             p.volatility, p.time_to_expiry, p.dividend_yield,
                             p.binomial_steps)
    if T <= 0 or σ <= 0:
        return 0.0
    dt = T / N
    u  = math.exp(σ * math.sqrt(dt))
    d  = 1 / u
    pu = (math.exp((r - q) * dt) - d) / (u - d)
    pd = 1 - pu
    disc = math.exp(-r * dt)
    prices = np.array([S * u**j * d**(N-j) for j in range(N+1)])
    vals   = np.maximum(prices - K, 0) if p.option_type=="call" else np.maximum(K - prices, 0)
    for _ in range(N):
        vals = disc * (pu * vals[1:] + pd * vals[:-1])
    return float(vals[0])'''

new_bin = '''def _binomial(p: ValuationParams) -> tuple:
    S, K, r, σ, T, q, N = (p.stock_price, p.strike_price, p.risk_free_rate,
                             p.volatility, p.time_to_expiry, p.dividend_yield,
                             p.binomial_steps)
    if T <= 0 or σ <= 0:
        return 0.0, {}
    dt = T / N
    u  = math.exp(σ * math.sqrt(dt))
    d  = 1 / u
    pu = (math.exp((r - q) * dt) - d) / (u - d)
    pd = 1 - pu
    disc = math.exp(-r * dt)
    prices = np.array([S * u**j * d**(N-j) for j in range(N+1)])
    vals   = np.maximum(prices - K, 0) if p.option_type=="call" else np.maximum(K - prices, 0)
    for _ in range(N):
        vals = disc * (pu * vals[1:] + pd * vals[:-1])
    detail = dict(u=u, d=d, p_up=pu, p_down=pd, dt=dt, steps=N, disc=disc)
    return float(vals[0]), detail'''

if old_bin in content:
    content = content.replace(old_bin, new_bin)
    print('OK: _binomial 置換成功')
else:
    print('NG: _binomial 置換失敗')

# ─── _mc 修正 ───
old_mc = '''def _mc(p: ValuationParams) -> float:
    S, K, r, σ, T, q = (p.stock_price, p.strike_price, p.risk_free_rate,
                         p.volatility, p.time_to_expiry, p.dividend_yield)
    if T <= 0 or σ <= 0:
        return 0.0
    rng = np.random.default_rng(42)
    Z   = rng.standard_normal(p.mc_simulations)
    ST  = S * np.exp((r - q - 0.5*σ**2)*T + σ*math.sqrt(T)*Z)
    payoff = np.maximum(ST - K, 0) if p.option_type=="call" else np.maximum(K - ST, 0)
    return float(np.exp(-r*T) * payoff.mean())'''

new_mc = '''def _mc(p: ValuationParams) -> tuple:
    S, K, r, σ, T, q = (p.stock_price, p.strike_price, p.risk_free_rate,
                         p.volatility, p.time_to_expiry, p.dividend_yield)
    if T <= 0 or σ <= 0:
        return 0.0, {}
    rng = np.random.default_rng(42)
    Z   = rng.standard_normal(p.mc_simulations)
    ST  = S * np.exp((r - q - 0.5*σ**2)*T + σ*math.sqrt(T)*Z)
    payoff = np.maximum(ST - K, 0) if p.option_type=="call" else np.maximum(K - ST, 0)
    price  = float(np.exp(-r*T) * payoff.mean())
    mean_p = float(payoff.mean())
    std_p  = float(payoff.std())
    se     = float(std_p / math.sqrt(p.mc_simulations))
    ci_lo  = float(np.exp(-r*T) * (mean_p - 1.96*se))
    ci_hi  = float(np.exp(-r*T) * (mean_p + 1.96*se))
    detail = dict(
        simulations=p.mc_simulations,
        mean=mean_p,
        std=std_p,
        se=se,
        ci_low=ci_lo,
        ci_high=ci_hi,
        payoffs=payoff,
    )
    return price, detail'''

if old_mc in content:
    content = content.replace(old_mc, new_mc)
    print('OK: _mc 置換成功')
else:
    print('NG: _mc 置換失敗')

with open('src/services/valuation_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('ファイル書き込み完了')
