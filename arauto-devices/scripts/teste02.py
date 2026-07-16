import tinytuya
c = tinytuya.Cloud()

# Tenta o endpoint genérico de informação do dispositivo
result = c.cloudrequest(f"/v1.0/devices/ebcdcefa1ca31d2db5etir")
print(result)