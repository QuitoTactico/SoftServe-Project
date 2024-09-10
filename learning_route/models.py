from django.db import models
from django.db.models import Subquery, OuterRef
from django.core.validators import MinValueValidator, MaxValueValidator
from skill.models import SkillLevel
from learning_resource.models import LearningResource

# id: int
# index: int
# level: int
# LearningRoute: LearningRoute
# learning_resource: LearningResource
# completed: bool
# time_spent: int

class LearningRouteResource(models.Model):
    id = models.AutoField(primary_key=True)
    index = models.IntegerField(validators=[MinValueValidator(0)], default=0)
    level = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], default=1)
    learning_resource = models.ForeignKey(LearningResource, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    time_spent = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    def __str__(self):
        return '[' + str(self.id) + '] ' + self.learning_resource.name + (' (Completed)' if self.completed else '')
    
    def set_completed(self):
        self.completed = True
        self.save()


# id: int
# skill_level: SkillLevel
# duration: int
# learning_route_resources: learningRouteResource[]
# actual_resource_index: int
# completed: bool
# time_spent: int

class LearningRoute(models.Model):
    id = models.AutoField(primary_key=True)
    skill_level = models.ForeignKey(SkillLevel, on_delete=models.CASCADE)
    duration = models.IntegerField(validators=[MinValueValidator(1)])
    learning_route_resources = models.ManyToManyField(LearningRouteResource, related_name='learning_routes', blank=True)
    actual_resource_index = models.IntegerField(default=0)
    completed = models.BooleanField(default=False)
    time_spent = models.IntegerField(validators=[MinValueValidator(0)], default=0)

    def __str__(self):
        return self.skill_level.skill.name + ' - ' + str(self.skill_level.level)
    
    def set_completed(self):
        self.completed = True
        self.save()

    @classmethod
    def generate(cls, user, skill_level: SkillLevel):
        learning_route = cls(skill_level=skill_level, duration=0)
        learning_route.save()

        learning_resources = LearningResource.objects.filter(
            skill=skill_level.skill,
            level__lte=skill_level.level
            # If you wanna use other order or filter, 
            # comment from here to the next comments and use what you want
        ).annotate(   
            required_skill_level=Subquery(
                SkillLevel.objects.filter(
                    skill=skill_level.skill,
                    required_skills__learningresource=OuterRef('pk')
                ).values('level')[:1]
            ),
            learning_skill_level=Subquery(
                SkillLevel.objects.filter(
                    skill=skill_level.skill,
                    learning_skills__learningresource=OuterRef('pk')
                ).values('level')[:1]
            )
        ).order_by('general_level', 'required_skill_level', 'learning_skill_level')
        #).order_by('general_level', 'required_skills__level', 'learning_skills__level')
        #).order_by('general_level')
        #).order_by('level', 'required_skills', 'learning_skills')


        # Create LearningRouteResource instances and add them to the learning route
        for index, resource in enumerate(learning_resources):
            route_resource = LearningRouteResource.objects.create(
                index=index,
                level=resource.level,
                learning_resource=resource
            )
            learning_route.learning_route_resources.add(route_resource)

        # Update the duration of the learning route
        learning_route.duration = sum(resource.duration for resource in learning_resources)
        learning_route.save()

        return learning_route