from tortoise.models import Model
from tortoise import fields

class Wallet(Model):
    id = fields.IntField(pk=True)
    private = fields.TextField()
    nick = fields.TextField()
    balance = fields.FloatField()