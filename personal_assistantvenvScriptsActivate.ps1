[1mdiff --git a/robo/services/ai_service.py b/robo/services/ai_service.py[m
[1mindex aefd9dd..4a8461c 100644[m
[1m--- a/robo/services/ai_service.py[m
[1m+++ b/robo/services/ai_service.py[m
[36m@@ -149,3 +149,4 @@[m [mclass AIService:[m
             self.PRIMARY_PROVIDER,[m
         )[m
         return response.choices[0].message.content.strip()[m
[41m+[m
