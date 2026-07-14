local tokens_key = KEYS[1]
local timestamp_key = KEYS[2]

local capacity = tonumber(ARGV[1])
local token_fill_rate = tonumber(ARGV[2])
local current_time = tonumber(ARGV[3])

local fill_time = capacity/token_fill_rate
local ttl = math.floor(fill_time*2)

local filled_tokens = tonumber(redis.call("GET", tokens_key))
local last_refill = tonumber(redis.call("GET", timestamp_key))

if filled_tokens == nil then
    filled_tokens = capacity
end

if last_refill == nil then 
    last_refill = current_time
end

filled_tokens = math.min(capacity, filled_tokens+((current_time-last_refill) * token_fill_rate))

local allowed = 0

if filled_tokens >= 1 then 
    allowed = 1
    filled_tokens = filled_tokens - 1
end

redis.call("SETEX",tokens_key,ttl,filled_tokens)
redis.call("SETEX",timestamp_key,ttl,current_time)
    
return {allowed, filled_tokens}









