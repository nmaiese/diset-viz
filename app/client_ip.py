"""L'IP del client dietro Cloudflare e Cloud Run, per i limiti di richiesta.

Il servizio sta dietro Cloudflare (DEPLOY.md). Nei log di Cloud Run l'indirizzo
della connessione (`httpRequest.remoteIp`, l'ultimo elemento di
`X-Forwarded-For`, aggiunto dal frontend di Google e non falsificabile) e'
sempre un edge Cloudflare: verificato il 30/09/2026 su 40 richieste a /quiz. Se
ci si fidasse di quello, tutti i giocatori di uno stesso edge dividerebbero il
limite. Regola: se l'ultimo hop e' un IP Cloudflare, il client e' quello di
`CF-Connecting-IP`, che Cloudflare scrive e sovrascrive; altrimenti (chiamata
diretta a run.app, test, locale) il client e' l'ultimo hop e `CF-Connecting-IP`
non si legge, perche' lo potrebbe aver scritto chiunque.

Gli intervalli sono quelli pubblicati da Cloudflare (https://www.cloudflare.com/ips-v4
e ips-v6), copiati il 30/09/2026. Cambiano di rado: se Cloudflare ne aggiunge uno, un
edge nuovo finisce nel caso "ultimo hop" e il limite torna condiviso, non aggirabile.
"""

import ipaddress

CLOUDFLARE_NETWORKS = tuple(ipaddress.ip_network(r) for r in (
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32",
    "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32",
))


def _ip(value):
    try:
        return ipaddress.ip_address((value or "").strip())
    except ValueError:
        return None


def is_cloudflare(value):
    ip = _ip(value)
    return ip is not None and any(ip in network for network in CLOUDFLARE_NETWORKS)


def resolve_client_ip(forwarded_for, cf_connecting_ip):
    """L'IP del client da `X-Forwarded-For` e `CF-Connecting-IP` su Cloud Run.
    None se non c'e' un ultimo hop leggibile."""
    hops = [h.strip() for h in (forwarded_for or "").split(",") if h.strip()]
    if not hops:
        return None
    last_hop = hops[-1]
    if is_cloudflare(last_hop):
        client = _ip(cf_connecting_ip)
        if client is not None:
            return str(client)
    return last_hop


def bucket_key(value):
    """La chiave del secchio di un limite di frequenza per un IP. Un IPv6 vale per il
    suo /64: un client ruota gli indirizzi dentro il prefisso che gli assegna il
    provider, e un secchio per indirizzo si aggirerebbe cambiando indirizzo. Un IPv4
    resta se stesso (anche quando arriva come IPv6 mappato), e un valore che non e'
    un IP resta com'e'."""
    ip = _ip(value)
    if ip is None:
        return value
    if ip.version == 6:
        if ip.ipv4_mapped is not None:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)
